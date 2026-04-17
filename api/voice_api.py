import os
import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from db.redis import redis_db

# --- INITIAL SETUP ---
# app.py handle karega "/voice" prefix ko, yahan router clean rakha hai
router = APIRouter(tags=["Voice Engine"])

# Environment Variables (Ensure ye Render Dashboard par set hon)
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")

# --- MODELS ---
class CallRequest(BaseModel):
    to_phone: str
    customer_id: str

# --- INTERNAL HELPER FUNCTIONS ---

def place_vapi_call(to_phone: str, customer_id: str):
    """
    Direct function jo Vapi infrastructure ko hit karta hai.
    Ise call_api.py se bhi import kiya ja sakta hai.
    """
    if not VAPI_API_KEY or not VAPI_ASSISTANT_ID:
        print("❌ CRITICAL: Vapi Credentials Missing")
        return None

    url = "https://api.vapi.ai/call/phone"
    
    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "customer": {
            "number": to_phone,
            "name": customer_id
        },
        "metadata": {
            "customer_id": customer_id
        }
    }
    
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"❌ Vapi API Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error in place_vapi_call: {e}")
        return None

# --- API ENDPOINTS ---

@router.post("/start")
async def start_voice_call(request: CallRequest):
    """
    Frontend Dialer hit karta hai: POST /voice/start
    """
    # 1. Check Wallet Balance in Redis
    # Key format: wallet:mantu_admin
    balance = redis_db.get(f"wallet:{request.customer_id}")
    
    if balance is None:
        # Agar key nahi milti toh safety ke liye default 0 set karo
        redis_db.set(f"wallet:{request.customer_id}", "0.0")
        balance = "0.0"

    if float(balance) <= 0:
        raise HTTPException(status_code=402, detail="Paise khatam ho gaye hain! Recharge karein.")

    # 2. Trigger the AI Call
    result = place_vapi_call(request.to_phone, request.customer_id)
    
    if not result:
        raise HTTPException(status_code=500, detail="Vapi server se connection fail ho gaya.")

    call_id = result.get("id")

    # 3. Initial Billing Entry (Optional)
    try:
        from services.billing_service import start_call_bill
        start_call_bill(call_id, request.customer_id)
    except Exception as e:
        print(f"⚠️ Billing Start Warning: {e}")

    return {
        "status": "success",
        "call_id": call_id,
        "message": "Vaani AI Assistant dialing now..."
    }

@router.post("/webhook")
async def vapi_webhook_handler(request: Request):
    """
    Vapi hits this after call ends: POST /voice/webhook
    """
    try:
        data = await request.json()
        message_type = data.get("type")

        if message_type == "end-of-call-report":
            call_id = data.get("id")
            customer_id = data.get("metadata", {}).get("customer_id", "unknown")
            duration = data.get("duration", 0) # in seconds
            transcript = data.get("transcript", "")

            # Call end logic: Paise kaatna aur logs save karna
            try:
                from services.billing_service import stop_call_billing
                from services.call_log_service import save_call_log
                
                # Deduct balance
                bill = stop_call_billing(call_id, customer_id, duration)
                
                # Update Dashboard Log
                save_call_log({
                    "call_sid": call_id,
                    "customer_id": customer_id,
                    "duration_sec": duration,
                    "status": "completed",
                    "cost": bill.get("cost") if bill else 0
                })
            except Exception as service_err:
                print(f"⚠️ Post-call service error: {service_err}")

        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Webhook Crash: {e}")
        return {"status": "error"}

@router.get("/health")
async def health():
    return {"status": "Voice API is fully functional"}
