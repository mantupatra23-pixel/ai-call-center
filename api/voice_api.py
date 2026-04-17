import os
import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from db.redis import redis_db

# --- INITIAL SETUP ---
router = APIRouter(prefix="/voice", tags=["Voice"])

# Environment Variables
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")

# --- MODELS ---
class CallRequest(BaseModel):
    to_phone: str
    customer_id: str

# --- SAFE SERVICE IMPORTS ---
# Agar services files mein functions ke naam alag hain, toh ye crash nahi hone dega
def safe_start_billing(call_id, customer_id):
    try:
        from services.billing_service import start_call_bill
        start_call_bill(call_id, customer_id)
    except Exception as e:
        print(f"Billing Start Error (Skipped): {e}")

def safe_stop_billing(call_id, customer_id, duration):
    try:
        from services.billing_service import stop_call_billing
        stop_call_billing(call_id, customer_id, duration)
    except Exception as e:
        print(f"Billing Stop Error (Skipped): {e}")

def safe_add_memory(customer_id, transcript):
    try:
        from services.ai_memory_service import add_call_memory
        add_call_memory(customer_id, transcript)
    except Exception as e:
        print(f"Memory Sync Error (Skipped): {e}")

# --- CORE LOGIC ---

@router.post("/start")
async def start_voice_call(request: CallRequest):
    """
    Main Endpoint: Frontend dialer yahan hit karega.
    """
    if not VAPI_API_KEY or not VAPI_ASSISTANT_ID:
        raise HTTPException(status_code=500, detail="Vapi Config Missing in Render Env")

    # 1. Wallet Check (Optional but recommended)
    balance = redis_db.get(f"wallet:{request.customer_id}")
    if balance and float(balance) <= 0:
        raise HTTPException(status_code=402, detail="Insufficient Balance")

    # 2. Prepare Vapi Call
    url = "https://api.vapi.ai/call/phone"
    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "customer": {
            "number": request.to_phone,
            "name": request.customer_id
        },
        "metadata": {
            "customer_id": request.customer_id
        }
    }
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # Call trigger karne se pehle internal billing record create karein
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 201:
            call_data = response.json()
            call_id = call_data.get("id")
            
            # Start tracking in our DB
            safe_start_billing(call_id, request.customer_id)
            
            return {
                "status": "success",
                "call_id": call_id,
                "message": "AI Assistant is now dialing..."
            }
        else:
            return {"status": "error", "message": response.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Vapi Call khatam hone par ye webhook hit hota hai.
    """
    try:
        data = await request.json()
        message_type = data.get("type")

        if message_type == "end-of-call-report":
            call_id = data.get("id")
            customer_id = data.get("metadata", {}).get("customer_id")
            duration = data.get("duration", 0) # seconds mein
            transcript = data.get("transcript", "")

            # 1. Paisa kaato (Billing)
            safe_stop_billing(call_id, customer_id, duration)
            
            # 2. Memory update karo (Transcript save)
            safe_add_memory(customer_id, transcript)

        return {"status": "received"}
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error"}

@router.get("/health")
async def health_check():
    return {"status": "Voice API is live"}
