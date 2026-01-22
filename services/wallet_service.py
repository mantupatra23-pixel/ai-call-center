from db.redis import redis_db

CALL_RATE_PER_MIN = 2.0   # ₹2 per minute (admin can change)

def get_balance(customer_id: str) -> float:
    bal = redis_db.get(f"wallet:{customer_id}")
    return float(bal) if bal else 0.0


def add_balance(customer_id: str, amount: float):
    redis_db.incrbyfloat(f"wallet:{customer_id}", amount)


def deduct_balance(customer_id: str, minutes: float):
    cost = minutes * CALL_RATE_PER_MIN
    redis_db.incrbyfloat(f"wallet:{customer_id}", -cost)
    return cost


def has_sufficient_balance(customer_id: str) -> bool:
    return get_balance(customer_id) > 0
