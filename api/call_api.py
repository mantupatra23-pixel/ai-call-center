#api/call_api.py

from fastapi import APIRouter, HTTPException
from services.wallet_service import has_sufficient_balance, get_balance
from services.safety_service import can_make_call, register_call_start
from services.revenue_guard_service import can_start_call
from services.notification_service import notify_low_balance
from services.dnc_service import is_dnc
from services.working_hours_service import is_within_hours
from db.redis import redis_db
from rq import Queue
from redis import Redis
from api.voice_api import place_call

router = APIRouter(prefix="/call", tags=["Call"])

redis_conn = Redis.from_url(redis_db.connection_pool.connection_kwargs["host"])
call_queue = Queue("calls", connection=redis_conn)


@router.post("/start")
def start_call(customer_id: str, to_phone: str):

    # 1️⃣ DNC check
    if is_dnc(customer_id, to_phone):
        raise HTTPException(400, "Number is in Do-Not-Call list")

    # 2️⃣ Working hours check
    if not is_within_hours(customer_id):
        raise HTTPException(400, "Outside working hours")

    # 3️⃣ Minimum balance (REVENUE GUARD)
    if not can_start_call(customer_id):
        raise HTTPException(400, "Low balance. Please recharge to place calls.")

    # 4️⃣ Low balance alert (optional)
    bal = get_balance(customer_id)
    if bal < 50:
        notify_low_balance(customer_id, bal)

    # 5️⃣ Wallet exists check (legacy safety)
    if not has_sufficient_balance(customer_id):
        raise HTTPException(400, "Insufficient wallet balance")

    # 6️⃣ Safety / rate limit check
    ok, reason = can_make_call(customer_id)
    if not ok:
        raise HTTPException(400, reason)

    # 7️⃣ Selected calling number
    from_number = redis_db.get(f"customer:{customer_id}:selected_number")
    if not from_number:
        raise HTTPException(400, "No calling number selected")

    # 8️⃣ Register call start
    register_call_start(customer_id)

    # 9️⃣ Enqueue call
    job = call_queue.enqueue(
        place_call,
        to_phone,
        from_number,
        customer_id
    )

    return {
        "queued": True,
        "job_id": job.id,
        "from": from_number,
        "to": to_phone
    }
