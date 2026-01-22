from db.redis import redis_db
from datetime import datetime
import pytz

def set_hours(customer_id: str, start: int, end: int, tz: str):
    """
    start/end: hour in 24h format (e.g. 10, 18)
    tz: timezone string (Asia/Kolkata, Asia/Dubai)
    """
    redis_db.hset(
        f"hours:{customer_id}",
        mapping={"start": start, "end": end, "tz": tz}
    )

def is_within_hours(customer_id: str) -> bool:
    data = redis_db.hgetall(f"hours:{customer_id}")
    if not data:
        return True  # default allow

    tz = pytz.timezone(data["tz"])
    now = datetime.now(tz).hour
    start, end = int(data["start"]), int(data["end"])
    return start <= now < end
