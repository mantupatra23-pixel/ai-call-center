import os
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# Internal Imports
from db.redis import redis_db
from api.voice_api import place_vapi_call # Hum Vapi wala function use karenge
from services.wallet_service import has_sufficient_balance
from services.dnc_service import is_dnc
from services.working_hours_service import is_within_hours
from services.safety_service import can_make_call

router = APIRouter(tags=["Call"])

# 1. Request Schema
class StartCallRequest(BaseModel):
    customer_id: str
    to_phone: str

# 2. START CALL ENDPOINT
@router.post("/start")
async def start_call(data: StartCallRequest):
    """
    Vapi AI Engine ke zariye call start karega (Twilio Bypass).
    Endpoint: /call/start
    """
    customer_id = data.customer_id
    to_phone = data.to_phone

    # --- VALIDATIONS ---
    # 1. DNC Check
    if is_dnc(customer_id, to_phone):
        raise HTTPException(status_code=400, detail="Number is in Do-Not-Call registry")

    # 2. Working Hours Check
    if not is_within_hours(customer_id):
        raise HTTPException(status_code=400, detail="Outside working hours")

    # 3. Wallet Safety Check
    if not has_sufficient_balance(customer_id):
        raise HTTPException(status_code=402, detail="Insufficient wallet balance. Please refill.")

    # 4. Rate Limit / Abuse Protection
    ok, reason = can_make_call(customer_id)
    if not ok:
        raise HTTPException(status_code=429, detail=reason)

    # --- VAPI ORCHESTRATION ---
    try:
        # Hum seedha Vapi engine ko call kar rahe hain jo Twilio bypass karega
        result = place_vapi_call(to_phone, customer_id)
        
        if not result or "id" not in result:
            raise HTTPException(status_code=500, detail="Voice Engine (Vapi) failed to respond")

        return {
            "status": "success",
            "queued": True,
            "call_id": result.get("id"),
            "customer_id": customer_id,
            "to": to_phone,
            "provider": "Vapi_HighSpeed_AI"
        }

    except Exception as e:
        print(f"CRITICAL ERROR in call_api: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# 3. END CALL ENDPOINT
@router.post("/end")
async def end_call(call_id: str):
    """
    Manual call termination logic.
    """
    from services.billing_service import stop_call_billing
    from services.active_call_service import remove_active_call

    # Note: Vapi call duration webhook se handle hoti hai, ye manual end ke liye hai
    bill = stop_call_billing(call_id, "manual_end", 0)
    remove_active_call(call_id)

    return {
        "status": "request_sent",
        "message": "Call termination signal sent"
    }
