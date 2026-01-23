# services/billing_service.py

import time
import json
from db.redis import redis_db

from services.wallet_service import deduct_balance
from services.subscription_service import (
    is_subscription_active,
    consume_minutes
)

# ===============================
# CONFIG
# ===============================
PER_MIN_RATE_KEY = "admin:call_rate_per_min"
BILLING_LOG_KEY = "billing:logs"


# ===============================
# CALL START (TEMP SAVE)
# ===============================
def start_call_billing(call_sid: str, customer_id: str):
    """
    Call connect hote hi temp data save
    """
    redis_db.set(
        f"call:{call_sid}",
        json.dumps({
            "customer_id": customer_id,
            "start_time": int(time.time())
        })
    )
    return True


# ===============================
# CALL END (FINAL BILLING)
# ===============================
def end_call_billing(call_sid: str):
    """
    Call end billing:
    - Duration calculate
    - Subscription first
    - Wallet fallback
    - Billing logs
    """

    raw = redis_db.get(f"call:{call_sid}")
    if not raw:
        return None

    data = json.loads(raw)
    customer_id = data["customer_id"]
    start_time = data["start_time"]

    end_time = int(time.time())
    duration_sec = max(1, end_time - start_time)
    minutes_used = (duration_sec + 59) // 60  # round up

    bill = {
        "call_sid": call_sid,
        "customer_id": customer_id,
        "duration_sec": duration_sec,
        "minutes": minutes_used,
        "timestamp": int(time.time())
    }

    # ===============================
    # 1️⃣ SUBSCRIPTION FIRST
    # ===============================
    if is_subscription_active(customer_id):
        consume_minutes(customer_id, minutes_used)

        bill.update({
            "billed_from": "subscription",
            "rate_per_min": 0,
            "cost": 0
        })

    else:
        # ===============================
        # 2️⃣ WALLET FALLBACK
        # ===============================
        rate_raw = redis_db.get(PER_MIN_RATE_KEY)
        rate = float(rate_raw) if rate_raw else 2.0  # safe default ₹2

        cost = minutes_used * rate
        remaining_balance = deduct_balance(customer_id, cost)

        bill.update({
            "billed_from": "wallet",
            "rate_per_min": rate,
            "cost": cost,
            "balance_after": remaining_balance
        })

    # ===============================
    # SAVE BILLING LOG
    # ===============================
    redis_db.lpush(BILLING_LOG_KEY, json.dumps(bill))

    # ===============================
    # CLEANUP TEMP DATA
    # ===============================
    redis_db.delete(f"call:{call_sid}")

    return bill


# ===============================
# MANUAL BILLING LOGGER
# (refund / adjustment / admin entry)
# ===============================
def log_billing(data: dict):
    redis_db.lpush(BILLING_LOG_KEY, json.dumps(data))
    return True
