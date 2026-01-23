# services/booking_service.py

import time, json
from db.redis import redis_db

def save_booking(call_sid, phone, intent):
    booking = {
        "call_sid": call_sid,
        "phone": phone,
        "intent": intent,
        "status": "booked",
        "created_at": int(time.time())
    }

    redis_db.hset("sales:bookings", call_sid, json.dumps(booking))
    redis_db.rpush("sales:booking_ids", call_sid)

    return booking
