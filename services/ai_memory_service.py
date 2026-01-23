# services/ai_memory_service.py

import json
import time
from db.redis import redis_db

# ==============================
# CONFIG
# ==============================
CALL_MEMORY_LIMIT = 10        # last 10 turns
LONG_MEMORY_LIMIT = 50        # last 50 events
SUMMARY_EVERY_N_CALLS = 3

# ==============================
# SHORT TERM MEMORY (CALL)
# ==============================
def add_call_memory(call_sid: str, role: str, text: str):
    key = f"mem:call:{call_sid}"
    redis_db.rpush(key, f"{role}: {text}")
    redis_db.ltrim(key, -CALL_MEMORY_LIMIT, -1)
    redis_db.expire(key, 3600)  # auto cleanup after 1 hour


def get_call_memory(call_sid: str) -> str:
    key = f"mem:call:{call_sid}"
    history = redis_db.lrange(key, 0, -1)
    return "\n".join(history)


# ==============================
# LONG TERM MEMORY (CUSTOMER)
# ==============================
def add_customer_memory(customer_id: str, data: dict):
    key = f"mem:customer:{customer_id}"

    record = {
        "time": int(time.time()),
        "data": data
    }

    redis_db.rpush(key, json.dumps(record))
    redis_db.ltrim(key, -LONG_MEMORY_LIMIT, -1)


def get_customer_memory(customer_id: str) -> list:
    key = f"mem:customer:{customer_id}"
    raw = redis_db.lrange(key, 0, -1)
    return [json.loads(r) for r in raw]


# ==============================
# SMART SUMMARY MEMORY
# ==============================
def save_summary(customer_id: str, summary: str):
    redis_db.set(
        f"mem:summary:{customer_id}",
        summary
    )


def get_summary(customer_id: str) -> str:
    return redis_db.get(f"mem:summary:{customer_id}") or ""


# ==============================
# AUTO SUMMARY COUNTER
# ==============================
def increment_call_count(customer_id: str):
    key = f"mem:count:{customer_id}"
    return redis_db.incr(key)


def should_summarize(customer_id: str) -> bool:
    count = int(redis_db.get(f"mem:count:{customer_id}") or 0)
    return count % SUMMARY_EVERY_N_CALLS == 0
