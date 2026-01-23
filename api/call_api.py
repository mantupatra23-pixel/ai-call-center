# api/call_api.py

import os
import time
from fastapi import APIRouter, HTTPException
from redis import Redis
from rq import Queue

from db.redis import redis_db
from api.voice_api import place_call

from services.wallet_service import (
    has_sufficient_balance,
    get_balance,
)
from services.safety_service import can_make_call
from services.revenue_guard_service import can_start_call
from services.notification_service import notify_low_balance
from services.dnc_service import is_dnc
from services.working_hours_service import is_within_hours
from services.call_registry_service import register_call_start

from services.billing_service import (
    start_call_billing,
    end_call_billing,
)

from services.active_call_service import (
    add_active_call,
    remove_active_call,
)

# ===============================
# ROUTER
# ===============================
router = APIRouter(prefix="/call", tags=["Call"])

# ===============================
# REDIS + QUEUE
# ===============================
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL missing")

redis_conn = Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

call_queue = Queue(
    "calls",
    connection=redis_conn
)

# ===============================
# START CALL
# ===============================
@router.post("/start")
def start_call(customer_id: str, to_phone: str):
    """
    Customer ke assigned Twilio number se call start karega
    """

    # 1️⃣ DNC check
    if is_dnc(customer_id, to_phone):
        raise HTTPException(400, "Number is in Do-Not-Call list")

    # 2️⃣ Working hours check
    if not is_within_hours(customer_id):
        raise HTTPException(400, "Outside working hours")

    # 3️⃣ Revenue guard (minimum balance / plan)
    if not can_start_call(customer_id):
        raise HTTPException(400, "Low balance. Please recharge")

    # 4️⃣ Low balance warning (soft)
    balance = get_balance(customer_id)
    if balance < 50:
        notify_low_balance(customer_id, balance)

    # 5️⃣ Wallet hard safety
    if not has_sufficient_balance(customer_id):
        raise HTTPException(400, "Insufficient wallet balance")

    # 6️⃣ Rate limit / abuse protection
    ok, reason = can_make_call(customer_id)
    if not ok:
        raise HTTPException(400, reason)

    # 7️⃣ Customer assigned Twilio number
    from_number = redis_db.get(f"customer:{customer_id}:from_number")
    if not from_number:
        raise HTTPException(400, "No calling number assigned to customer")

    # 8️⃣ Register call (analytics / concurrency)
    register_call_start(customer_id)

    # 9️⃣ Generate internal Call SID
    call_sid = f"call_{int(time.time())}_{customer_id}"

    # 🔟 Start billing timer
    start_call_billing(call_sid, customer_id)

    # 🔴 ADD ACTIVE CALL (LIVE DASHBOARD)
    add_active_call(
        call_sid=call_sid,
        customer_id=customer_id,
        to_phone=to_phone
    )

    # 1️⃣1️⃣ Enqueue async call
    job = call_queue.enqueue(
        place_call,
        to_phone,
        from_number,
        customer_id,
        call_sid
    )

    return {
        "queued": True,
        "job_id": job.id,
        "call_sid": call_sid,
        "from": from_number,
        "to": to_phone,
        "customer_id": customer_id
    }

# ===============================
# END CALL (Webhook / Manual)
# ===============================
@router.post("/end")
def end_call(call_sid: str):
    """
    Call end webhook / manual trigger
    """

    bill = end_call_billing(call_sid)
    if not bill:
        raise HTTPException(404, "Call not found or already ended")

    # 🔴 REMOVE ACTIVE CALL (LIVE DASHBOARD)
    remove_active_call(call_sid)

    return {
        "status": "call_ended",
        "billing": bill
    }
