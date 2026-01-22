from db.redis import redis_db

IDEMP_TTL = 60 * 60 * 24   # 24 hours

def is_processed(key: str) -> bool:
    return redis_db.exists(f"idemp:{key}") == 1

def mark_processed(key: str):
    redis_db.setex(f"idemp:{key}", IDEMP_TTL, "1")
