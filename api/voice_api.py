import os
import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from db.redis import redis_db

# --- INITIAL SETUP ---
router = APIRouter(prefix="/voice", tags=["Voice Engine"])

# Env Variables
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")

class CallRequest(BaseModel):
    to_phone: str
    customer_id: str

# --- THE MISSING FUNCTION (Fixes ImportError) ---
def place_vapi_call(to_phone: str, customer_id: str):
    """
    Direct function for internal imports in call_api.py
    """
    if not VAPI_API_KEY or not VAPI_ASSISTANT_ID:
        print("❌ Vapi Config Missing")
        return None

    url = "https://api.vapi.ai/call/phone"
    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "customer": {"number": to_phone, "name": customer_id},
        "metadata": {"customer_id": customer_id}
    }
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return response.json()
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# --- ROUTES ---

@router.post("/start")
async def start_voice_call(request: CallRequest):
    result = place_vapi_call(request.to_phone, request.customer_id)
    if not result:
        raise HTTPException(status_code=500, detail="Call trigger failed")
    
    return {"status": "success", "call_id": result.get("id")}

@router.post("/webhook")
async def vapi_webhook(request: Request):
    data = await request.json()
    # Billing & Memory logic yahan add karein (as per previous updates)
    return {"status": "ok"}
