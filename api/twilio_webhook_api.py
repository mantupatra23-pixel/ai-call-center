# api/twilio_webhook_api.py

import time
from fastapi import APIRouter, Request

from services.billing_service import (
    start_call_billing,
    end_call_billing,
)

from services.call_log_service import (
    save_call_log,
    update_call_log,
)

from services.idempotency_service import (
    is_processed,
    mark_processed,
)

from services.notification_service import notify_low_balance
from services.wallet_service import get_balance

from services.call_registry_service import (
    get_call,
    delete_call,
)

from services.active_call_service import remove_active_call

router = APIRouter(prefix="/twilio", tags=["Twilio"])

# =====================================================
# TWILIO CALL STATUS WEBHOOK
# =====================================================
@router.post("/call-status")
async def call_status(request: Request):
    """
    Twilio events:
    initiated -> ringing -> in-progress -> completed
    failed / busy / no-answer
    """

    form = await request.form()

    call_sid = form.get("CallSid")
    call_status = form.get("CallStatus")
    duration = int(form.get("CallDuration") or 0)

    from_number = form.get("From")
    to_number = form.get("To")

    # Get call registry (customer_id saved earlier)
    call = get_call(call_sid)
    customer_id = call["customer_id"] if call else None

    # =====================================================
    # IDEMPOTENCY (ANTI DOUBLE BILLING)
    # =====================================================
    unique_key = f"{call_sid}:{call_status}"
    if is_processed(unique_key):
        return {"ok": True, "duplicate": True}

    # =====================================================
    # RINGING / IN-PROGRESS → START BILLING SESSION
    # =====================================================
    if call_status in ("ringing", "in-progress"):
        start_call_billing(call_sid, customer_id)

        save_call_log({
            "call_sid": call_sid,
            "customer_id": customer_id,
            "from_number": from_number,
            "to_number": to_number,
            "status": call_status,
            "duration_sec": 0,
            "cost": 0.0,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    # =====================================================
    # COMPLETED → FINAL BILLING
    # =====================================================
    elif call_status == "completed":
        bill = end_call_billing(call_sid)

        update_call_log(call_sid, {
            "status": "completed",
            "duration_sec": duration,
            "cost": bill["cost"] if bill else 0,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        # 🔔 Low balance alert
        balance = get_balance(customer_id)
        if balance < 50:
            notify_low_balance(customer_id, balance)

        # 🧹 Cleanup registry
        delete_call(call_sid)

        # 🔴 REMOVE ACTIVE CALL (LIVE DASHBOARD)
        remove_active_call(call_sid)

    # =====================================================
    # FAILED / BUSY / NO-ANSWER
    # =====================================================
    elif call_status in ("failed", "busy", "no-answer"):
        update_call_log(call_sid, {
            "status": call_status,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        delete_call(call_sid)

        # 🔴 REMOVE ACTIVE CALL
        remove_active_call(call_sid)

    # =====================================================
    # MARK PROCESSED (VERY IMPORTANT)
    # =====================================================
    mark_processed(unique_key)

    return {
        "ok": True,
        "call_sid": call_sid,
        "status": call_status,
    }
