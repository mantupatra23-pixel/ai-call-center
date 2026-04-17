import os
from fastapi import APIRouter, Request
from services.recording_service import save_recording
from services.call_log_service import update_call_log

router = APIRouter(prefix="/vapi-recording", tags=["Vapi-Recording"])

@router.post("/callback")
async def vapi_recording_callback(request: Request):
    """
    Vapi se recording URL receive karke database mein save karega.
    """
    data = await request.json()
    
    # Vapi call object se data nikalna
    call_id = data.get("id")
    recording_url = data.get("recordingUrl")
    duration = data.get("duration", 0)
    customer_id = data.get("metadata", {}).get("customer_id", "unknown")

    if not recording_url:
        return {"ok": False, "message": "No recording URL found"}

    # Recording Object prepare karna
    rec = {
        "recording_sid": f"rec_{call_id}",
        "call_sid": call_id,
        "customer_id": customer_id,
        "recording_url": recording_url,
        "duration_sec": duration
    }

    # 1. Database mein save karo
    save_recording(rec)

    # 2. Call Log ko update karo recording link ke saath
    try:
        update_call_log(call_id, {
            "recording_url": recording_url
        })
    except Exception as e:
        print(f"Error updating call log with recording: {e}")

    return {"ok": True, "call_id": call_id}
