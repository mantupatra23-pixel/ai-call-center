import os
import json
import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from groq import Groq

# Core & DB Imports
from db.redis import redis_db
from core.auth_guard import get_current_user

# Services Logic (Ensure these files exist in your services folder)
from services.ai_memory_service import add_call_memory
from services.billing_service import start_call_bill, stop_call_billing
from services.sales_service import detect_sales_intent

router = APIRouter(prefix="/voice", tags=["Voice"])

# ==========================================
# ENV LOADING
# ==========================================
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")

# ==========================================
# CLIENTS SETUP
# ==========================================
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

class CallRequest(BaseModel):
    to_phone: str
    customer_id: str

# ==========================================
# AI BRAIN (Groq Llama-3-70b)
# ==========================================
def get_ai_reply(history: list, user_input: str) -> str:
    """
    Optional: Custom processing agar Vapi ke bahar reply chahiye.
    """
    if not groq_client:
        return "Ji, main sun raha hoon. Kripya boliye."

    messages = [{"role": "system", "content": "You are Ananya, a helpful AI from Visora AI. Speak naturally in Hindi-English mix."}]
    for h in history[-5:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_input})

    completion = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=0.7,
        max_tokens=150
    )
    return completion.choices[0].message.content

# ==========================================
# VAPI CALL ENGINE (Twilio Bypass)
# ==========================================
def place_vapi_call(to_phone: str, customer_id: str):
    """
    Directly triggers a high-speed AI call using Vapi.ai
    """
    url = "https://api.vapi.ai/call/phone"
    
    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "customer": {
            "number": to_phone,
            "name": customer_id
        },
        "metadata": {
            "customer_id": customer_id,
            "source": "Vaani_AI_Dashboard"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"Vapi API Error: {response.text}")
            return None
    except Exception as e:
        print(f"Critical Call Error: {str(e)}")
        return None

# ==========================================
# ROUTES (Endpoints)
# ==========================================

@router.post("/start")
async def start_voice_call(request: CallRequest):
    """
    Endpoint for Frontend Dialer
    Path: /voice/start
    """
    # 1. Start Initial Billing Record
    temp_sid = f"vapi_{int(os.getpid())}"
    start_call_bill(temp_sid, request.customer_id)
    
    # 2. Trigger Call
    result = place_vapi_call(request.to_phone, request.customer_id)
    
    if not result:
        raise HTTPException(status_code=500, detail="Call engine failed to respond")

    # 3. Update Redis with real Vapi Call ID
    vapi_call_id = result.get("id")
    redis_db.set(f"call:customer:{vapi_call_id}", request.customer_id, ex=3600)

    return {
        "status": "success",
        "call_id": vapi_call_id,
        "provider": "vapi_ai",
        "message": "AI Assistant is dialing..."
    }

@router.post("/webhook")
async def vapi_callback_webhook(request: Request):
    """
    Vapi sends call reports here when call ends.
    """
    data = await request.json()
    message_type = data.get("type")
    
    if message_type == "end-of-call-report":
        call_id = data.get("id")
        customer_id = data.get("metadata", {}).get("customer_id", "unknown")
        duration = data.get("duration", 0) # seconds mein
        transcript = data.get("transcript", "")
        
        # 1. Stop Billing (Calculates cost based on duration)
        stop_call_billing(call_id, customer_id, duration)
        
        # 2. Add to AI Memory (For future calls)
        add_call_memory(customer_id, transcript)
        
        # 3. Detect Sales Intent (Marketing logic)
        intent = detect_sales_intent(transcript)
        if intent == "high":
            print(f"Hot Lead Detected for {customer_id}")

    return {"status": "received"}

@router.get("/status/{call_id}")
async def get_call_status(call_id: str):
    """
    Check if call is active or ended
    """
    url = f"https://api.vapi.ai/call/{call_id}"
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
    
    response = requests.get(url, headers=headers)
    return response.json()
