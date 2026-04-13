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

# ================= CORE =================
from db.redis import redis_db
from core.auth_guard import get_current_user

router = APIRouter(prefix="/voice", tags=["Voice"])

# ================= ENV =================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
BASE_URL = os.getenv("PUBLIC_BASE_URL")
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
            "text": text,
            "time": str(datetime.now())
        }))

def get_memory(call_sid):
    if not redis_conn:
        return []
    data = redis_conn.lrange(f"call:{call_sid}", 0, -1)
    return [json.loads(x) for x in data]

# ================= AI =================
def ai_reply(user_text: str, call_sid: str) -> str:
    if not groq_client:
        return "System error: AI not configured"

    history = get_memory(call_sid)

    messages = [
        {
            "role": "system",
            "content": "You are a smart Hindi AI call center agent. Speak politely, short, and sales focused."
        }
    ]

    for h in history[-5:]:
        messages.append({"role": "user", "content": h["text"]})

    messages.append({"role": "user", "content": user_text})

    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.5
        )

        reply = response.choices[0].message.content.strip()

    except Exception as e:
        print("AI ERROR:", e)
        reply = "Maaf kijiye, kuch error aa gaya."

    save_memory(call_sid, "user", user_text)
    save_memory(call_sid, "ai", reply)

    return reply

# ================= AZURE VOICE =================
def generate_voice(text: str) -> str:
    if not AZURE_KEY or not AZURE_REGION:
        return ""

    voice_dir = "static/voice"
    os.makedirs(voice_dir, exist_ok=True)

    # cleanup old files
    for f in os.listdir(voice_dir):
        path = os.path.join(voice_dir, f)
        if os.path.isfile(path):
            if os.path.getmtime(path) < (datetime.now() - timedelta(minutes=30)).timestamp():
                try:
                    os.remove(path)
                except:
                    pass

    fname = f"v_{abs(hash(text))}.mp3"
    file_path = os.path.join(voice_dir, fname)

    if not os.path.exists(file_path):
        try:
            speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
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

    return f"{BASE_URL}/{voice_dir}/{fname}"

# ================= TWILIO XML =================
def get_txml(audio_url: str, gather=True):
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response>'

    if audio_url:
        xml += f"<Play>{audio_url}</Play>"

    if gather:
        xml += f'''
        <Gather 
            input="speech"
            action="{BASE_URL}/voice/process"
            method="POST"
            timeout="4"
            speechTimeout="auto"
        />
        <Redirect>{BASE_URL}/voice/process</Redirect>
        '''

    xml += "</Response>"
    return xml

# ================= API =================

@router.post("/make-call")
def make_call(
    to: str = Query(...),
    from_: str = Query(...),
    user=Depends(get_current_user)
):
    if not twilio_client:
        raise HTTPException(500, "Twilio not configured")

    try:
        job = call_queue.enqueue(place_call, to, from_)
        return {"status": "queued", "job_id": job.id}
    except Exception as e:
        return {"error": str(e)}

@router.post("/start", response_class=PlainTextResponse)
async def start():
    msg = "Namaste! Main AI call assistant bol raha hoon. Kya main aapse baat kar sakta hoon?"
    audio = generate_voice(msg)
    return get_txml(audio)

@router.post("/process", response_class=PlainTextResponse)
async def process(request: Request):
    form = await request.form()

    call_sid = form.get("CallSid")
    speech = (form.get("SpeechResult") or "").strip()

    if not speech:
        reply = "Mujhe sunayi nahi diya, please dubara boliye."
    else:
        if any(x in speech.lower() for x in ["bye", "band", "nahi", "no"]):
            return "<Response><Hangup/></Response>"

        reply = ai_reply(speech, call_sid)

    audio = generate_voice(reply)
    return get_txml(audio)

@router.post("/status")
async def call_status(request: Request):
    form = await request.form()
    print("CALL STATUS:", dict(form))
    return {"ok": True}

# ================= WORKER =================
def place_call(to, from_):
    if not twilio_client:
        print("Twilio not configured")
        return

    try:
        call = twilio_client.calls.create(
            to=to,
            from_=from_,
            url=f"{BASE_URL}/voice/start",
            status_callback=f"{BASE_URL}/voice/status"
        )
        print("CALL STARTED:", call.sid)

    except TwilioRestException as e:
        print("TWILIO ERROR:", e)
