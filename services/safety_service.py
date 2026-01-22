from db.redis import redis_db
import time

# ---- CONFIG (ADMIN CONTROL) ----
MAX_CALLS_PER_DAY = 200
MAX_CALL_DURATION_SEC = 10 * 60   # 10 minutes
CALL_GAP_SEC = 10                 # min gap between calls

def _today_key(customer_id):
    return f"safety:{customer_id}:calls:{time.strftime('%Y-%m-%d')}"

def can_make_call(customer_id: str) -> tuple[bool, str]:
    # Admin block check
    if redis_db.get(f"customer:{customer_id}:blocked") == "1":
        return False, "Customer is blocked by admin"

    # Daily call limit
    today_key = _today_key(customer_id)
    calls_today = int(redis_db.get(today_key) or 0)
    if calls_today >= MAX_CALLS_PER_DAY:
        return False, "Daily call limit reached"

    # Rate limit (gap between calls)
    last_call = redis_db.get(f"safety:{customer_id}:last_call")
    if last_call:
        if time.time() - float(last_call) < CALL_GAP_SEC:
            return False, "Calling too fast, please wait"

    return True, "OK"


def register_call_start(customer_id: str):
    redis_db.incr(_today_key(customer_id))
    redis_db.set(f"safety:{customer_id}:last_call", time.time())


def is_duration_allowed(duration_sec: int) -> bool:
    return duration_sec <= MAX_CALL_DURATION_SEC
