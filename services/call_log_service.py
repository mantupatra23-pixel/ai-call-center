from db.redis import redis_db
import json

def save_call_log(log: dict):
    redis_db.set(f"call:{log['call_sid']}", json.dumps(log))
    redis_db.sadd(f"customer:{log['customer_id']}:calls", log["call_sid"])

def update_call_log(call_sid: str, updates: dict):
    raw = redis_db.get(f"call:{call_sid}")
    if not raw:
        return
    data = json.loads(raw)
    data.update(updates)
    redis_db.set(f"call:{call_sid}", json.dumps(data))

def get_customer_calls(customer_id: str):
    sids = redis_db.smembers(f"customer:{customer_id}:calls")
    logs = []
    for sid in sids:
        raw = redis_db.get(f"call:{sid}")
        if raw:
            logs.append(json.loads(raw))
    return logs
