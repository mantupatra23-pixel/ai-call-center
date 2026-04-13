import os, json, redis, azure.cognitiveservices.speech as speechsdk
from fastapi import APIRouter, Query, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from rq import Queue
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from datetime import datetime, timedelta
from groq import Groq  # Groq Integration

# Core & DB
from db.redis import redis_db
from core.auth_guard import get_current_user

# Services Logic
from services.ai_memory_service import add_call_memory, get_call_memory
from services.billing_service import start_call_billing, stop_call_billing
from services.sales_service import detect_sales_intent, upsell_reply

router = APIRouter(prefix="/voice", tags=["Voice"])

# ==========================================
# ENV LOADING
# ==========================================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Clients Setup
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID else None
redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
call_queue = Queue("calls", connection=redis_conn)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ==========================================
# UTILS & AI BRAIN (Groq)
# ==========================================

def get_ai_reply(history: list, user_input: str) -> str:
    """Groq Llama-3-70b se fast reply generate karta hai."""
    if not groq_client:
        return "Ji, main sun raha hoon. Kripya bolein."
    
    messages = [{"role": "system", "content": "You are a professional AI Assistant for Visora AI. Speak in natural Hinglish. Keep it short and human-like."}]
    # Add history
    for h in history[-5:]:
        messages.append({"role": "user" if h['role'] == 'User' else "assistant", "content": h['text']})
    messages.append({"role": "user", "content": user_input})

    completion = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=0.7,
        max_tokens=150
    )
    return completion.choices[0].message.content

def generate_voice(text: str) -> str:
    voice_dir = "static/voice"
    os.makedirs(voice_dir, exist_ok=True)
    fname = f"v_{abs(hash(text))}.mp3"
    path = f"{voice_dir}/{fname}"
    full_path = os.path.join(os.getcwd(), path)

    if not os.path.exists(full_path):
        if not AZURE_KEY: return ""
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=full_path)
        speech_config.speech_synthesis_voice_name = "hi-IN-MadhurNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        ssml = f"<speak version='1.0' xml:lang='hi-IN'><voice name='hi-IN-MadhurNeural'><mstts:express-as style='cheerful'><prosody rate='-5%'>{text}</prosody></mstts:express-as></voice></speak>"
        synthesizer.speak_ssml_async(ssml).get()

    return f"{BASE_URL}/{path}"

# Important for app.py imports
def place_call(to_phone: str, from_phone: str, customer_id: str):
    if not twilio_client: return print("Twilio not set")
    try:
        call = twilio_client.calls.create(
            machine_detection='Enable',
            to=to_phone,
            from_=from_phone,
            url=f"{BASE_URL}/voice/twilio-voice"
        )
        redis_db.set(f"call:customer:{call.sid}", customer_id)
        start_call_billing(call.sid, customer_id)
    except Exception as e:
        print(f"Call Error: {e}")

# ==========================================
# ROUTES
# ==========================================

@router.post("/twilio-voice", response_class=PlainTextResponse)
async def twilio_voice():
    welcome = "Namaskar! Main Visora AI se baat kar raha hoon. Kya main aapki koi madad kar sakta hoon?"
    audio = generate_voice(welcome)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Play>{audio}</Play>
        <Gather input="speech" timeout="5" action="{BASE_URL}/voice/process-speech" method="POST" interruptible="true"/>
    </Response>"""

@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid")
    user_text = (form.get("SpeechResult") or "").strip()
    
    if not user_text:
        return f'<Response><Play>{generate_voice("Maaf kijiye, main sun nahi paaya.")}</Play><Gather input="speech" action="{BASE_URL}/voice/process-speech"/></Response>'

    # Memory & AI Logic
    add_call_memory(call_sid, "User", user_text)
    history = get_call_memory(call_sid)
    
    # 1. Check Sales Intent
    intent = detect_sales_intent(user_text)
    reply = upsell_reply(intent)
    
    # 2. If no sales reply, use Groq
    if not reply:
        reply = get_ai_reply(history, user_text)

    add_call_memory(call_sid, "AI", reply)
    audio = generate_voice(reply)

    return f"""<Response>
        <Play>{audio}</Play>
        <Gather input="speech" action="{BASE_URL}/voice/process-speech" method="POST" interruptible="true"/>
    </Response>"""

@router.post("/call-status")
async def call_status(request: Request):
    form = await request.form()
    sid = form.get("CallSid")
    status = form.get("CallStatus")
    if status in ["completed", "failed"]:
        cid = redis_db.get(f"call:customer:{sid}")
        stop_call_billing(sid, cid)
    return {"status": "ok"}
