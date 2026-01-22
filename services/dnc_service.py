from db.redis import redis_db

def add_dnc(customer_id: str, phone: str):
    redis_db.sadd(f"dnc:{customer_id}", phone)

def remove_dnc(customer_id: str, phone: str):
    redis_db.srem(f"dnc:{customer_id}", phone)

def is_dnc(customer_id: str, phone: str) -> bool:
    return redis_db.sismember(f"dnc:{customer_id}", phone)
