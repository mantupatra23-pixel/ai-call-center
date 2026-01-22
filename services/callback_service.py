from db.redis import redis_db
import time, json, uuid

def schedule_callback(customer_id: str, to_phone: str, when_ts: int):
    job_id = str(uuid.uuid4())
    data = {
        "job_id": job_id,
        "customer_id": customer_id,
        "to_phone": to_phone,
        "when": when_ts,
        "status": "scheduled"
    }
    redis_db.set(f"callback:{job_id}", json.dumps(data))
    redis_db.zadd("callbacks:schedule", {job_id: when_ts})
    return job_id


def due_callbacks(now_ts: int):
    return redis_db.zrangebyscore("callbacks:schedule", 0, now_ts)


def mark_done(job_id: str):
    redis_db.zrem("callbacks:schedule", job_id)
