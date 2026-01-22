from db.redis import redis_db
import json, time, uuid

MAX_RETRIES = 3

def push_failed_webhook(payload: dict):
    job_id = str(uuid.uuid4())
    data = {
        "job_id": job_id,
        "payload": payload,
        "retries": 0,
        "created_at": time.time()
    }
    redis_db.lpush("dlq:webhooks", json.dumps(data))


def retry_failed_webhooks(handler_func):
    items = redis_db.lrange("dlq:webhooks", 0, -1)

    for raw in items:
        job = json.loads(raw)
        try:
            handler_func(job["payload"])
            redis_db.lrem("dlq:webhooks", 1, raw)
        except Exception:
            job["retries"] += 1
            redis_db.lrem("dlq:webhooks", 1, raw)

            if job["retries"] < MAX_RETRIES:
                redis_db.lpush("dlq:webhooks", json.dumps(job))
            # else drop (or admin alert)
