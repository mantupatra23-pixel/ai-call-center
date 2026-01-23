# api/twilio_recording_api.py

import json
import time
from fastapi import APIRouter, Request
from db.redis import redis_db

router = APIRouter(prefix="/twilio", tags=["Twilio-Recording"])

@router.post("/recording")
async def recording_callback(request: Request):
    form = await request.form()

    recording_sid = form.get("RecordingSid")
    call_sid = form.get("CallSid")
    recording_url = form.get("RecordingUrl")
    duration = int(form.get("RecordingDuration") or 0)

    # get customer mapping
    customer_id = redis_db.get(f"call:{call_sid}:customer")
    if not customer_id:
        return {"ignored": True}

    data = {
        "recording_sid": recording_sid,
        "call_sid": call_sid,
        "customer_id": customer_id,
        "url": recording_url + ".mp3",
        "duration_sec": duration,
        "created_at": int(time.time())
    }

    redis_db.rpush(
        f"customer:{customer_id}:recordings",
        json.dumps(data)
    )

    redis_db.rpush("recordings:all", json.dumps(data))

    return {"status": "saved"}
