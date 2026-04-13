import os
import json
import redis
import azure.cognitiveservices.speech as speechsdk
from fastapi import APIRouter, Query, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from rq import Queue
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from datetime import datetime, timedelta
from groq import Groq

# Core
from db.redis import redis_db
from core.auth_guard import get_current_user

# Services
from services.sales_service import detect_sales_intent, upsell_reply

router = APIRouter(prefix="/voice", tags=["Voice"])

# ================== ENV ==================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
BASE_URL = os.getenv("PUBLIC_BASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise Exception("❌ GROQ_API_KEY missing")

twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
call_queue = Queue("calls", connection=redis_conn)

groq_client = Groq(api_key=GROQ_API_KEY)

# ================== MEMORY ==================
def save_memory(call_sid, role, text):
    redis_conn.rpush(f"call:{call_sid}", json.dumps({"role": role, "text": text}))

def get_memory(call_sid):
    data = redis_conn.lrange(f"call:{call_sid}", 0, -1)
    return [json.loads(x) for x in data]

# ================== AI ==================
def ai_reply(user_text: str, call_sid: str) -> str:
    history = get_memory(call_sid)

    messages = [{"role": "system", "content": "You are a smart Hindi AI sales caller."}]
    
    for h in history[-5:]:
        messages.append({"role": "user" if h["role"]=="User" else "assistant", "content": h["text"]})

    messages.append({"role": "user", "content": user_text})

    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages
        )
        reply = response.choices[0].message.content
        save_memory(call_sid, "AI", reply)
        return reply
    except Exception as e:
        print("Groq Error:", e)
        return "System error, please try later."

# ================== AZURE VOICE ==================
def generate_voice(text: str) -> str:
    voice_dir = "static/voice"
    os.makedirs(voice_dir, exist_ok=True)

    fname = f"v_{abs(hash(text))}.mp3"
    path = f"{voice_dir}/{fname}"
    full_path = os.path.join(os.getcwd(), path)

    # cleanup old files
    for f in os.listdir(voice_dir):
        fpath = os.path.join(voice_dir, f)
        if os.path.getmtime(fpath) < (datetime.now() - timedelta(minutes=20)).timestamp():
            try: os.remove(fpath)
            except: pass

    if not os.path.exists(full_path):
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=full_path)

        speech_config.speech_synthesis_voice_name = "hi-IN-MadhurNeural"

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        synthesizer.speak_text_async(text).get()

    return f"{BASE_URL}/{path}"

# ================== TWILIO XML ==================
def get_txml(audio_url: str):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Play>{audio_url}</Play>
<Gather input="speech" action="{BASE_URL}/voice/process-speech" method="POST" speechTimeout="auto"/>
</Response>
"""

# ================== API ==================

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
async def twilio_voice(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid")

    msg = "Namaste! Main AI call assistant bol raha hoon. Kya main aapse baat kar sakta hoon?"
    save_memory(call_sid, "AI", msg)

    return get_txml(generate_voice(msg))


@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    form = await request.form()

    call_sid = form.get("CallSid")
    text = (form.get("SpeechResult") or "").strip()

    if not text:
        return get_txml(generate_voice("Mujhe sunayi nahi diya, please dobara boliye."))

    save_memory(call_sid, "User", text)

    # exit condition
    if any(x in text.lower() for x in ["bye", "band", "nahi", "stop"]):
        return f'<Response><Say>Dhanyavaad!</Say><Hangup/></Response>'

    # sales intent
    intent = detect_sales_intent(text)
    reply = upsell_reply(intent)

    if not reply:
        reply = ai_reply(text, call_sid)

    return get_txml(generate_voice(reply))


@router.post("/call-status")
async def call_status(request: Request):
    return {"status": "ok"}

# ================== WORKER ==================
def place_call(to_phone: str, from_phone: str, customer_id: str):
    try:
        call = twilio_client.calls.create(
            to=to_phone,
            from_=from_phone,
            url=f"{BASE_URL}/voice/twilio-voice",
            status_callback=f"{BASE_URL}/voice/call-status"
        )

        redis_db.set(f"call:customer:{call.sid}", customer_id)
        return {"status": "success"}

    except TwilioRestException as e:
        print("Twilio Error:", e)
        return {"status": "error"}
