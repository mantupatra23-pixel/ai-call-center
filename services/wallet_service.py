# services/wallet_service.py

from db.redis import redis_db

# =========================
# CONFIG
# =========================
CALL_RATE_PER_MIN = 2.0       # ₹2 per minute (future: admin configurable)
DEFAULT_MIN_BALANCE = 10.0    # Safety buffer to avoid negative calls


# =========================
# GET BALANCE
# =========================
def get_balance(customer_id: str) -> float:
    bal = redis_db.get(f"wallet:{customer_id}")
    return float(bal) if bal else 0.0


# =========================
# ADD BALANCE
# =========================
def add_balance(customer_id: str, amount: float) -> float:
    if amount <= 0:
        raise ValueError("Amount must be positive")

    redis_db.incrbyfloat(f"wallet:{customer_id}", amount)
    return get_balance(customer_id)


# =========================
# DEDUCT BALANCE (DIRECT)
# =========================
def deduct_balance(customer_id: str, amount: float) -> float:
    if amount <= 0:
        raise ValueError("Amount must be positive")

    redis_db.incrbyfloat(f"wallet:{customer_id}", -amount)
    return get_balance(customer_id)


# =========================
# DEDUCT BY CALL DURATION
# =========================
def deduct_by_minutes(customer_id: str, minutes: float) -> float:
    if minutes <= 0:
        return 0.0

    cost = round(minutes * CALL_RATE_PER_MIN, 2)
    redis_db.incrbyfloat(f"wallet:{customer_id}", -cost)
    return cost


# =========================
# BALANCE CHECK
# =========================
def has_sufficient_balance(customer_id: str) -> bool:
    return get_balance(customer_id) >= DEFAULT_MIN_BALANCE


# =========================
# HARD BLOCK CHECK (CALL START)
# =========================
def can_start_call(customer_id: str) -> bool:
    """
    Use this before starting Twilio call
    """
    return has_sufficient_balance(customer_id)
