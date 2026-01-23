import os
import redis

# Redis URL (Upstash / Local दोनों के लिए)
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL missing")

# ✅ Redis client (STRING SAFE)
redis_db = redis.from_url(
    REDIS_URL,
    decode_responses=True,   # 🔥 VERY IMPORTANT
)
