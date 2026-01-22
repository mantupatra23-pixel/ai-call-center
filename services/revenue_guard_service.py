from db.redis import redis_db
from services.wallet_service import get_balance

# ---- ADMIN CONFIG ----
MIN_START_BALANCE = 10.0   # ₹10 minimum to start call
GRACE_BUFFER = 5.0         # ₹5 buffer during call

def can_start_call(customer_id: str) -> bool:
    bal = get_balance(customer_id)
    return bal >= MIN_START_BALANCE

def has_grace_balance(customer_id: str) -> bool:
    bal = get_balance(customer_id)
    return bal >= GRACE_BUFFER
