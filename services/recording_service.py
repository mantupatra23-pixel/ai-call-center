from db.redis import redis_db
import json

def save_recording(rec: dict):
    redis_db.set(f"recording:{rec['recording_sid']}", json.dumps(rec))
    redis_db.sadd(f"customer:{rec['customer_id']}:recordings", rec["recording_sid"])

def get_customer_recordings(customer_id: str):
    sids = redis_db.smembers(f"customer:{customer_id}:recordings")
    items = []
    for sid in sids:
        raw = redis_db.get(f"recording:{sid}")
        if raw:
            items.append(json.loads(raw))
    return items
