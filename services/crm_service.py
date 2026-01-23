# services/crm_service.py

import json, time
from db.redis import redis_db

def create_lead(call_sid, phone, intent, emotion="neutral"):
    lead = {
        "call_sid": call_sid,
        "phone": phone,
        "intent": intent,
        "emotion": emotion,
        "status": "new",
        "created_at": int(time.time())
    }

    redis_db.hset("crm:leads", call_sid, json.dumps(lead))
    redis_db.rpush("crm:lead_ids", call_sid)
    return lead

def update_lead_status(call_sid, status):
    raw = redis_db.hget("crm:leads", call_sid)
    if not raw:
        return False

    lead = json.loads(raw)
    lead["status"] = status
    redis_db.hset("crm:leads", call_sid, json.dumps(lead))
    return True

def list_leads():
    ids = redis_db.lrange("crm:lead_ids", 0, -1)
    out = []
    for i in ids:
        raw = redis_db.hget("crm:leads", i)
        if raw:
            out.append(json.loads(raw))
    return out
