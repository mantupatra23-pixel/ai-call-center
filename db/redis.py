import os
import redis

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL missing")

redis_db = redis.from_url(
    REDIS_URL,
    decode_responses=True
)
