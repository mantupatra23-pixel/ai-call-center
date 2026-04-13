import os
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from redis import Redis
from rq import Queue

# Internal Imports (Aapke existing structure ke hisaab se)
from db.redis import redis_db
from api.voice_api import place_call
from services.wallet_service import get_balance, has_sufficient_balance
from services.safety_service import can_make_call
from services.revenue_guard_service import can_start_call
from services.notification_service import notify_low_balance
from services.dnc_service import is_dnc
from services.working_hours_service import is_within_hours
from services.call_registry_service import register_call_start
from services.billing_service import start_call_billing, stop_call_billing
from services.active_call_service import add_active_call, remove_active_call

# 1. Router Setup (Prefix removed to avoid /call/call/start issue)
router = APIRouter(tags=["Call"])

# 2. Redis & Queue Setup
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL missing in environment variables")

redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
call_queue = Queue("calls", connection=redis_conn)

# 3. Request Schema (JSON Body handle karne ke liye)
class StartCallRequest(BaseModel):
    customer_id: str
    to_phone: str

# 4. START CALL ENDPOINT
@router.post("/start")
async def start_call(data: StartCallRequest):
    """
    Customer ke assigned Twilio number se call start karne ke liye.
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

    # 3. Revenue Guard / Wallet Safety
    if not can_start_call(customer_id):
        raise HTTPException(status_code=402, detail="Low balance. Please refill.")

    if not has_sufficient_balance(customer_id):
        raise HTTPException(status_code=402, detail="Insufficient wallet balance")

    # 4. Rate Limit / Abuse Protection
    ok, reason = can_make_call(customer_id)
    if not ok:
        raise HTTPException(status_code=429, detail=reason)

    # --- CALL ORCHESTRATION ---
    # 5. Get Assigned Twilio Number
    from_number = redis_db.get(f"customer:{customer_id}:phone")
    if not from_number:
        raise HTTPException(status_code=404, detail="No calling number assigned to this customer")

    # 6. Generate IDs and Start Processes
    call_sid = f"call_{int(time.time())}_{customer_id}"
    register_call_start(customer_id)
    start_call_billing(call_sid, customer_id)
    add_active_call(call_sid, customer_id, to_phone)

    # 7. Enqueue Async Call
    job = call_queue.enqueue(
        place_call,
        to_phone,
        from_number,
        customer_id
    )

    return {
        "queued": True,
        "job_id": job.id,
        "call_sid": call_sid,
        "from": from_number,
        "to": to_phone,
        "customer_id": customer_id
    }

# 5. END CALL ENDPOINT
@router.post("/end")
async def end_call(call_sid: str):
    """
    Call end webhook or manual trigger.
    Endpoint: /call/end
    """
    bill = stop_call_billing(call_sid)
    if not bill:
        raise HTTPException(status_code=404, detail="Call not found or already ended")

    remove_active_call(call_sid)

    return {
        "status": "call_ended",
        "billing": bill
    }
