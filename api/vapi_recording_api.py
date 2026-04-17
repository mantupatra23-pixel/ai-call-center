import json
import time
import os
from fastapi import APIRouter, Request
from db.redis import redis_db

router = APIRouter(prefix="/vapi-recording", tags=["Vapi-Recording"])

@router.post("/callback")
async def vapi_recording_callback(request: Request):
    """
    Vapi Call khatam hone par recording data Redis mein save karega.
    """
    try:
        # Vapi bhejta hai JSON data
        data = await request.json()
        
        call_id = data.get("id")
        recording_url = data.get("recordingUrl")
        duration = data.get("duration", 0)
        
        # Metadata se customer_id nikalna (Jo humne call start ke waqt bheja tha)
        customer_id = data.get("metadata", {}).get("customer_id")

        if not customer_id:
            # Agar metadata missing hai toh Redis se lookup karne ki koshish karein
            customer_id = redis_db.get(f"call:{call_id}:customer")
            if not customer_id:
                return {"ignored": True, "reason": "No customer mapping found"}

        # Recording Data Object prepare karein
        recording_data = {
            "recording_sid": f"vrec_{call_id}",
            "call_sid": call_id,
            "customer_id": customer_id,
            "url": recording_url,
            "duration_sec": duration,
            "created_at": int(time.time())
        }

        # 1. Individual Customer ki recording list mein push karein
        redis_db.rpush(
            f"customer:{customer_id}:recordings",
            json.dumps(recording_data)
        )

        # 2. Global recordings list mein push karein (Admin Dashboard ke liye)
        redis_db.rpush("recordings:all", json.dumps(recording_data))

        # 3. Call Log update (Optional: Agar SQL use kar rahe hain toh)
        try:
            from services.call_log_service import update_call_log
            update_call_log(call_id, {"recording_url": recording_url})
        except:
            pass

        return {"status": "saved", "call_id": call_id}

    except Exception as e:
        print(f"Recording Callback Error: {e}")
        return {"status": "error", "message": str(e)}
