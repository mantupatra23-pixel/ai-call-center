# services/live_billing_service.py

import json
from db.redis import redis_db
from services.wallet_service import deduct_balance, get_balance

CHECK_INTERVAL_COST = 0.5  # ₹ per 30 sec (example)

def live_deduct(customer_id: str):
    balance = get_balance(customer_id)

    if balance <= 0:
        return False, 0

    remaining = deduct_balance(customer_id, CHECK_INTERVAL_COST)
    return remaining > 0, remaining
