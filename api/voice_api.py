import os
import json
import redis
import requests
import azure.cognitiveservices.speech as speechsdk
from fastapi import APIRouter, Query, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from rq import Queue
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from datetime import datetime, timedelta

# Project Core & DB
from db.redis import redis_db
from core.auth_guard import get_current_user

# AI & Services Logic
from services.ai_agent_service import ai_reply
from services.ai_memory_service import (
    add_call_memory, get_call_memory
)
from services.billing_service import start_call_billing, stop_call_billing
from services.crm_service import create_lead
from services.whatsapp_service import send_whatsapp
from services.sales_service import detect_sales_intent, upsell_reply
from services.booking_service import save_booking

# =================================================================
# SETUP & ENV
# =================================================================
router = APIRouter(prefix="/voice", tags=["Voice"])

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
BASE_URL = os.getenv("PUBLIC_BASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION")

twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
call_queue = Queue("calls", connection=redis_conn)

# =================================================================
# AZURE VOICE
# =================================================================
def generate_voice(text: str) -> str:
    voice_dir = "static/voice"
    os.makedirs(voice_dir, exist_ok=True)

    fname = f"v_{abs(hash(text))}.mp3"
    path = f"{voice_dir}/{fname}"
    full_path = os.path.join(os.getcwd(), path)

    if not os.path.exists(full_path):
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=full_path)

        speech_config.speech_synthesis_voice_name = "hi-IN-MadhurNeural"

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'>
            <voice name='hi-IN-MadhurNeural'>
                {text}
            </voice>
        </speak>
        """

        synthesizer.speak_ssml_async(ssml).get()

    return f"{BASE_URL}/{path}"

# =================================================================
# TWILIO RESPONSE
# =================================================================
def get_txml(audio_url: str):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>{audio_url}</Play>
<Gather input="speech" action="{BASE_URL}/voice/process-speech" method="POST"/>
</Response>
"""

# =================================================================
# API
# =================================================================

@router.post("/make-call")
def make_call(
    to_phone: str = Query(...),
    from_phone: str = Query(...),
    user=Depends(get_current_user)
):
    if not to_phone.startswith("+"):
        raise HTTPException(400, "Use +91 format")

    job = call_queue.enqueue(place_call, to_phone, from_phone, user["id"])
    return {"status": "queued", "job_id": job.id}


@router.post("/twilio-voice", response_class=PlainTextResponse)
async def twilio_voice():
    msg = "Namaste! Main AI assistant bol raha hoon."
    return get_txml(generate_voice(msg))


@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    form = await request.form()
    text = (form.get("SpeechResult") or "").strip()

    if not text:
        return get_txml(generate_voice("Please repeat"))

    reply = ai_reply(text)

    return get_txml(generate_voice(reply))


@router.post("/call-status")
async def call_status(request: Request):
    form = await request.form()
    sid = form.get("CallSid")

    stop_call_billing(sid, "user")
    return {"status": "ok"}

# =================================================================
# WORKER
# =================================================================
def place_call(to_phone: str, from_phone: str, customer_id: str):
    try:
        call = twilio_client.calls.create(
            to=to_phone,
            from_=from_phone,  # ✅ IMPORTANT FIX
            url=f"{BASE_URL}/voice/twilio-voice",
            status_callback=f"{BASE_URL}/voice/call-status"
        )

        redis_db.set(f"call:customer:{call.sid}", customer_id)
        start_call_billing(call.sid, customer_id)

        return {"status": "success"}

    except TwilioRestException as e:
        print("Twilio Error:", e)
        return {"status": "error"}
