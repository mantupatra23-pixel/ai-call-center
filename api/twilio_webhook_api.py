import time
from fastapi import APIRouter, Request

from services.call_log_service import (
    save_call_log,
    update_call_log,
)

from services.wallet_service import (
    deduct_balance,
    get_balance,
)

from services.safety_service import is_duration_allowed
from services.idempotency_service import (
    is_processed,
    mark_processed,
)

from services.revenue_guard_service import has_grace_balance
from services.notification_service import notify_low_balance


router = APIRouter(
    prefix="/twilio",
    tags=["Twilio"]
)

# =====================================================
# TWILIO CALL STATUS WEBHOOK
# =====================================================
@router.post("/call-status")
async def call_status(request: Request):
    """
    Twilio will hit this webhook automatically
    ringing -> in-progress -> completed / failed
    """

    form = await request.form()

    call_sid = form.get("CallSid")
    call_status = form.get("CallStatus")
    duration = int(form.get("CallDuration") or 0)

    from_number = form.get("From")
    to_number = form.get("To")

    # Custom field passed while creating call
    customer_id = form.get("CustomerId") or "unknown"

    # -------------------------------------------------
    # IDEMPOTENCY (ANTI DUPLICATE)
    # -------------------------------------------------
    unique_key = f"{call_sid}:{call_status}"

    if is_processed(unique_key):
        return {"ok": True, "duplicate": True}

    # -------------------------------------------------
    # RINGING / IN-PROGRESS
    # -------------------------------------------------
    if call_status in ("ringing", "in-progress"):
        save_call_log({
            "call_sid": call_sid,
            "customer_id": customer_id,
            "from_number": from_number,
            "to_number": to_number,
            "status": call_status,
            "duration_sec": 0,
            "cost": 0.0,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    # -------------------------------------------------
    # COMPLETED
    # -------------------------------------------------
    elif call_status == "completed":

        cost = 0.0

        # 🔐 SAFETY + GRACE BALANCE CHECK
        if is_duration_allowed(duration) and has_grace_balance(customer_id):
            minutes = max(1, duration // 60)
            cost = deduct_balance(customer_id, minutes)

        update_call_log(call_sid, {
            "status": "completed",
            "duration_sec": duration,
            "cost": cost,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        # 🔔 LOW BALANCE ALERT (POST CALL)
        balance = get_balance(customer_id)
        if balance < 50:
            notify_low_balance(customer_id, balance)

    # -------------------------------------------------
    # FAILED / BUSY / NO-ANSWER
    # -------------------------------------------------
    elif call_status in ("failed", "busy", "no-answer"):
        update_call_log(call_sid, {
            "status": call_status,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    # -------------------------------------------------
    # MARK PROCESSED (VERY IMPORTANT)
    # -------------------------------------------------
    mark_processed(unique_key)

    return {"ok": True}
