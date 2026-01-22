from db.redis import redis_db
import json

def save_memory(customer_id: str, phone: str, summary: str):
    key = f"memory:{customer_id}:{phone}"
    redis_db.set(key, summary)

def get_memory(customer_id: str, phone: str):
    return redis_db.get(f"memory:{customer_id}:{phone}")
