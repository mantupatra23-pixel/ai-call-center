# services/active_call_service.py

import time
from db.redis import redis_db
import json

ACTIVE_CALLS_KEY = "calls:active"

def add_active_call(call_sid: str, customer_id: str, to_phone: str):
    redis_db.hset(
        ACTIVE_CALLS_KEY,
        call_sid,
        json.dumps({
            "call_sid": call_sid,
            "customer_id": customer_id,
            "to": to_phone,
            "started_at": int(time.time())
        })
    )

def remove_active_call(call_sid: str):
    redis_db.hdel(ACTIVE_CALLS_KEY, call_sid)

def list_active_calls():
    calls = []
    raw = redis_db.hgetall(ACTIVE_CALLS_KEY)
    for sid, data in raw.items():
        call = json.loads(data)
        call["duration_sec"] = int(time.time()) - call["started_at"]
        calls.append(call)
    return calls

def list_customer_calls(customer_id: str):
    return [
        c for c in list_active_calls()
        if c["customer_id"] == customer_id
    ]
