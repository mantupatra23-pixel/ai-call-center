from db.redis import redis_db
import time

LOW_BALANCE_THRESHOLD = 50.0  # ₹50

def notify_low_balance(customer_id: str, balance: float):
    # simple flag + log (later WhatsApp/Email)
    redis_db.lpush(
        "alerts:low_balance",
        f"{time.time()}|{customer_id}|{balance}"
    )
