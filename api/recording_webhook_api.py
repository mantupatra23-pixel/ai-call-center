from fastapi import APIRouter, Request
from services.recording_service import save_recording
from services.call_log_service import update_call_log

router = APIRouter(prefix="/twilio", tags=["Twilio-Recording"])

# ---- RECORDING CALLBACK ----
@router.post("/recording")
async def recording_callback(request: Request):
    form = await request.form()

    recording_sid = form.get("RecordingSid")
    call_sid = form.get("CallSid")
    recording_url = form.get("RecordingUrl")
    duration = int(form.get("RecordingDuration") or 0)
    customer_id = form.get("CustomerId")

    if not (recording_sid and call_sid and recording_url and customer_id):
        return {"ok": False}

    rec = {
        "recording_sid": recording_sid,
        "call_sid": call_sid,
        "customer_id": customer_id,
        "recording_url": recording_url + ".mp3",  # convenient
        "duration_sec": duration
    }

    save_recording(rec)

    # attach recording to call log
    update_call_log(call_sid, {
        "recording_url": rec["recording_url"]
    })

    return {"ok": True}
