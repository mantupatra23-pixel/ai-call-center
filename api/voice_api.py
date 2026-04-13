import os
import json
import redis
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from rq import Queue
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import azure.cognitiveservices.speech as speechsdk
from groq import Groq

# ================= ROUTER =================
router = APIRouter(prefix="/voice", tags=["Voice"])

# ================= ENV =================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL")
AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ================= SAFE INIT =================
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
redis_conn = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None
call_queue = Queue("calls", connection=redis_conn) if redis_conn else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ================= MEMORY =================
def save_memory(call_sid, role, text):
    if redis_conn:
        redis_conn.rpush(f"call:{call_sid}", json.dumps({
            "role": role,
            "text": text
        }))

def get_memory(call_sid):
    if not redis_conn:
        return []
    data = redis_conn.lrange(f"call:{call_sid}", 0, -1)
    return [json.loads(x) for x in data]

# ================= AI =================
def ai_reply(user_text: str, call_sid: str) -> str:
    if not groq_client:
        return "System not ready"

    history = get_memory(call_sid)

    messages = [
        {"role": "system", "content": "Reply in Hindi, short, polite, like a call agent."}
    ]

    for h in history[-5:]:
        messages.append({"role": "user", "content": h["text"]})

    messages.append({"role": "user", "content": user_text})

    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages
        )

        reply = response.choices[0].message.content.strip()

    except Exception as e:
        print("AI ERROR:", e)
        reply = "Sorry, system error."

    save_memory(call_sid, "user", user_text)
    save_memory(call_sid, "ai", reply)

    return reply

# ================= VOICE =================
def generate_voice(text: str) -> str:
    if not AZURE_KEY or not AZURE_REGION or not BASE_URL:
        return ""

    voice_dir = "static/voice"
    os.makedirs(voice_dir, exist_ok=True)

    fname = f"v_{abs(hash(text))}.mp3"
    file_path = os.path.join(voice_dir, fname)

    if not os.path.exists(file_path):
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=AZURE_KEY,
                region=AZURE_REGION
            )
            audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)

            speech_config.speech_synthesis_voice_name = "hi-IN-MadhurNeural"

            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config
            )

            synthesizer.speak_text_async(text).get()

        except Exception as e:
            print("TTS ERROR:", e)
            return ""

    return f"{BASE_URL}/static/voice/{fname}"

# ================= TWILIO XML =================
def get_txml(audio_url: str):
    return f"""
    <Response>
        <Play>{audio_url}</Play>
        <Gather input="speech" action="{BASE_URL}/voice/process" method="POST"/>
    </Response>
    """

# ================= API =================

@router.post("/make-call")
def make_call(to: str = Query(...), from_: str = Query(...)):
    if not twilio_client:
        return {"error": "Twilio not configured"}

    try:
        call = twilio_client.calls.create(
            to=to,
            from_=from_,
            url=f"{BASE_URL}/voice/start"
        )
        return {"status": "calling", "sid": call.sid}
    except TwilioRestException as e:
        return {"error": str(e)}

@router.post("/start", response_class=PlainTextResponse)
async def start():
    msg = "Namaste! Main AI assistant bol raha hoon."
    audio = generate_voice(msg)
    return get_txml(audio)

@router.post("/process", response_class=PlainTextResponse)
async def process(request: Request):
    form = await request.form()

    call_sid = form.get("CallSid", "default")
    speech = (form.get("SpeechResult") or "").strip()

    if not speech:
        reply = "Mujhe sunayi nahi diya, dubara boliye."
    else:
        if any(x in speech.lower() for x in ["bye", "band", "no"]):
            return "<Response><Hangup/></Response>"

        reply = ai_reply(speech, call_sid)

    audio = generate_voice(reply)
    return get_txml(audio)

@router.post("/status")
async def status(request: Request):
    form = await request.form()
    print("STATUS:", dict(form))
    return {"ok": True}
