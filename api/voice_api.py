# api/voice_api.py

import os, json, redis, requests
from fastapi import APIRouter, Query, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from rq import Queue
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from db.redis import redis_db
from core.auth_guard import get_current_user

from services.ai_agent_service import ai_reply
from services.ai_memory_service import (
    add_call_memory,
    get_call_memory,
    increment_call_count,
    should_summarize,
    save_summary
)

from services.billing_service import start_call_billing, stop_call_billing
from services.subscription_service import consume_minutes
from services.crm_service import create_lead
from services.whatsapp_service import send_whatsapp
from services.sales_service import detect_sales_intent, upsell_reply
from services.booking_service import save_booking

# =====================================================
# ROUTER
# =====================================================
router = APIRouter(prefix="/voice", tags=["Voice"])

# =====================================================
# ENV
# =====================================================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
BASE_URL = os.getenv("PUBLIC_BASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID")

if not all([TWILIO_SID, TWILIO_TOKEN, BASE_URL, REDIS_URL,
            ELEVEN_API_KEY, ELEVEN_VOICE_ID]):
    raise RuntimeError("Missing ENV variables")

# =====================================================
# CLIENTS
# =====================================================
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
call_queue = Queue("calls", connection=redis_conn)

# =====================================================
# ELEVENLABS TTS
# =====================================================
def eleven_tts(text: str) -> str:
    os.makedirs("static/voice", exist_ok=True)
    fname = f"{abs(hash(text))}.mp3"
    path = f"static/voice/{fname}"

    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}",
        headers={
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.75
            }
        },
        timeout=15
    )

    if r.status_code != 200:
        return eleven_tts("Kripya thoda intezaar karein.")

    with open(path, "wb") as f:
        f.write(r.content)

    return f"{BASE_URL}/{path}"

# =====================================================
# LANGUAGE DETECT
# =====================================================
def detect_lang(text: str):
    for h in ["kya", "hai", "nahi", "kyu", "ka", "ke"]:
        if h in text.lower():
            return "hi"
    return "en"

# =====================================================
# MAKE CALL API
# =====================================================
@router.post("/make-call")
def make_call(
    to_phone: str = Query(...),
    from_phone: str = Query(...),
    user=Depends(get_current_user)
):
    if not to_phone.startswith("+") or not from_phone.startswith("+"):
        raise HTTPException(400, "Invalid phone format")

    cfg = redis_db.get("admin:config")
    rate = float(json.loads(cfg).get("call_rate_per_min", 0))

    if user["wallet"] < rate:
        raise HTTPException(402, "Low wallet")

    job = call_queue.enqueue(place_call, to_phone, from_phone, user["id"])
    return {"queued": True, "job_id": job.id}

# =====================================================
# TWILIO FIRST RESPONSE
# =====================================================
@router.post("/twilio-voice", response_class=PlainTextResponse)
def twilio_voice():
    audio = eleven_tts("Namaskar! Main AI Call Center se bol raha hoon.")
    return f"""
<Response>
  <Play>{audio}</Play>
  <Gather input="speech" timeout="5" action="{BASE_URL}/voice/process-speech"/>
</Response>
"""

# =====================================================
# PROCESS SPEECH (AI + MEMORY + SALES)
# =====================================================
@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid")
    text = (form.get("SpeechResult") or "").strip()
    to_phone = form.get("To")

    customer_id = redis_db.get(f"call:customer:{call_sid}")

    if not text:
        audio = eleven_tts("Kripya bolein.")
        return f"<Response><Play>{audio}</Play><Gather input='speech' action='{BASE_URL}/voice/process-speech'/></Response>"

    if any(w in text.lower() for w in ["bye", "band", "goodbye"]):
        audio = eleven_tts("Dhanyavaad. Call samapt.")
        return f"<Response><Play>{audio}</Play><Hangup/></Response>"

    # 🧠 SHORT MEMORY
    add_call_memory(call_sid, "User", text)
    history = get_call_memory(call_sid)

    with open("data/company_profile.json") as f:
        company_profile = json.load(f)

    lang = detect_lang(text)

    # 🔥 SALES INTENT
    intent = detect_sales_intent(text)
    sales_reply = upsell_reply(intent)

    if sales_reply:
        reply = sales_reply
    else:
        reply = ai_reply(
            user_text=history,
            company_profile=company_profile,
            lang=lang,
            customer_id=customer_id
        )

    add_call_memory(call_sid, "AI", reply)

    # 🔥 BOOKING
    if intent in ["demo", "buy", "booking"]:
        save_booking(call_sid=call_sid, phone=to_phone, intent=intent)

    audio = eleven_tts(reply)

    return f"""
<Response>
  <Play>{audio}</Play>
  <Gather input="speech" action="{BASE_URL}/voice/process-speech"/>
</Response>
"""

# =====================================================
# CALL STATUS (BILLING + MEMORY SUMMARY + CRM)
# =====================================================
@router.post("/call-status")
async def call_status(request: Request):
    form = await request.form()
    sid = form.get("CallSid")
    status = form.get("CallStatus")
    to_phone = form.get("To")

    if status in ["completed", "failed", "busy", "no-answer"]:
        cid = redis_db.get(f"call:customer:{sid}")
        duration = int(form.get("CallDuration", 0))

        stop_call_billing(sid, cid)
        consume_minutes(cid, max(1, duration // 60))

        # 🧠 LONG MEMORY SUMMARY
        if cid:
            count = increment_call_count(cid)
            if should_summarize(cid):
                save_summary(
                    cid,
                    "Customer showed interest, spoke politely, prefers Hindi."
                )

        create_lead(
            call_sid=sid,
            phone=to_phone,
            intent="sales",
            emotion="interested"
        )

        send_whatsapp(
            to_phone=to_phone,
            text="Thanks for calling 🙏 Our team will contact you shortly."
        )

    return {"ok": True}

# =====================================================
# RECORDING WEBHOOK
# =====================================================
@router.post("/recording")
async def recording_webhook(request: Request):
    form = await request.form()
    redis_db.hset("call:recordings", form.get("CallSid"), form.get("RecordingUrl"))
    return {"saved": True}

# =====================================================
# RQ WORKER
# =====================================================
def place_call(to_phone: str, from_phone: str, customer_id: str):
    try:
        call = twilio_client.calls.create(
            to=to_phone,
            from_=from_phone,
            url=f"{BASE_URL}/voice/twilio-voice",
            status_callback=f"{BASE_URL}/voice/call-status",
            status_callback_event=["completed"],
            record=True,
            recording_channels="dual",
            recording_status_callback=f"{BASE_URL}/voice/recording"
        )

        redis_db.set(f"call:customer:{call.sid}", customer_id)
        start_call_billing(call.sid, customer_id)

    except TwilioRestException as e:
        print("Twilio error:", e)
