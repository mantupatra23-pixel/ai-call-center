import time
from fastapi import APIRouter, Request
from db.redis import redis_db

# Services Logic Imports
from services.billing_service import stop_call_billing
from services.call_log_service import save_call_log, update_call_log
from services.idempotency_service import is_processed, mark_processed
from services.notification_service import notify_low_balance
from services.wallet_service import get_balance
from services.active_call_service import remove_active_call

router = APIRouter(prefix="/vapi", tags=["Vapi-Webhook"])

@router.post("/webhook")
async def vapi_callback(request: Request):
    """
    Vapi Call khatam hone par billing aur logging handle karega.
    """
    data = await request.json()
    message_type = data.get("type")
    
    # Hum sirf call khatam hone wali report par action lenge
    if message_type != "end-of-call-report":
        return {"status": "ignored", "type": message_type}

    call_id = data.get("id")
    customer_id = data.get("metadata", {}).get("customer_id", "unknown")
    duration = data.get("duration", 0) # Duration in seconds
    status = data.get("endedReason", "completed")
    
    # IDEMPOTENCY (Anti-Double Billing)
    unique_key = f"vapi_proc:{call_id}"
    if is_processed(unique_key):
        return {"ok": True, "duplicate": True}

    # 1. FINAL BILLING & LOGGING
    # Billing service se paise kato
    bill = stop_call_billing(call_id, customer_id, duration)
    
    # Call history mein save karo
    save_call_log({
        "call_sid": call_id,
        "customer_id": customer_id,
        "status": status,
        "duration_sec": duration,
        "cost": bill.get("cost") if bill else 0,
        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    })

    # 2. LOW BALANCE ALERT
    balance = get_balance(customer_id)
    if balance and float(balance) < 50:
        notify_low_balance(customer_id, balance)

    # 3. CLEANUP (Remove from Live Dashboard)
    remove_active_call(call_id)
    
    # Mark as processed
    mark_processed(unique_key)

    return {
        "ok": True, 
        "call_id": call_id, 
        "status": "processed"
    }
