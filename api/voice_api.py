import os
import json
import redis
import requests

from rq import Queue
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# =====================================================
# ROUTER
# =====================================================
router = APIRouter()

# =====================================================
# ENV
# =====================================================
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_NUMBER")
BASE_URL = os.getenv("PUBLIC_BASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID")

if not BASE_URL:
    raise RuntimeError("PUBLIC_BASE_URL missing")

# =====================================================
# CLIENTS
# =====================================================
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

redis_conn = redis.from_url(
    REDIS_URL,
    decode_responses=True
)

call_queue = Queue("calls", connection=redis_conn)

# =====================================================
# HELPERS
# =====================================================
def detect_language(text: str):
    text = text.lower()

    if any("\u0600" <= c <= "\u06FF" for c in text):
        return "ar-SA", "arabic"

    if any(w in text for w in ["kya", "hai", "nahi", "rupaye", "namaste"]):
        return "hi-IN", "hindi"

    return "en-US", "english"


def detect_emotion(text: str):
    text = text.lower()

    if any(w in text for w in ["problem", "complaint", "issue", "angry"]):
        return "angry"
    if any(w in text for w in ["thanks", "thank you", "great"]):
        return "happy"
    if any(w in text for w in ["sad", "bad", "disappointed"]):
        return "sad"

    return "neutral"


def match_intent(text, intents, fallback):
    text = text.lower()
    for key, reply in intents.items():
        if key in text:
            return reply
    return fallback


def save_call_log(phone, text, emotion):
    os.makedirs("data", exist_ok=True)
    path = "data/call_logs.json"

    logs = []
    if os.path.exists(path):
        with open(path) as f:
            logs = json.load(f)

    logs.append({
        "phone": phone,
        "text": text,
        "emotion": emotion
    })

    with open(path, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)


def elevenlabs_tts(text, emotion="neutral"):
    if not ELEVEN_API_KEY or not ELEVEN_VOICE_ID:
        return None

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "voice_settings": {
                "stability": 0.3 if emotion == "angry" else 0.6,
                "similarity_boost": 0.85
            }
        }

        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code != 200:
            return None

        os.makedirs("static/voice", exist_ok=True)
        audio_path = "static/voice/output.mp3"

        with open(audio_path, "wb") as f:
            f.write(r.content)

        return "/static/voice/output.mp3"

    except Exception as e:
        print("ELEVENLABS ERROR:", e)
        return None


# =====================================================
# WORKER FUNCTION (RQ)
# =====================================================
def place_call(phone: str):
    try:
        call = twilio_client.calls.create(
            to=phone,
            from_=TWILIO_PHONE,
            url=f"{BASE_URL}/voice/twilio-voice",
            record=True
        )
        print("CALL STARTED:", call.sid)
    except TwilioRestException as e:
        print("TWILIO ERROR:", e)


# =====================================================
# API ENDPOINTS
# =====================================================
@router.post("/make-call")
def make_call(phone: str = Query(...)):
    if not phone.startswith("+"):
        raise HTTPException(400, "Phone must be in +91XXXXXXXXXX format")

    job = call_queue.enqueue(place_call, phone)

    return {
        "queued": True,
        "job_id": job.id,
        "phone": phone
    }


@router.post("/twilio-voice", response_class=PlainTextResponse)
def twilio_voice():
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="hi-IN">
        Namaskar! Hello! Marhaban!
        Main AI Call Center se bol raha hoon.
    </Say>
    <Gather input="speech" action="{BASE_URL}/voice/process-speech" />
</Response>
"""


@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    form = await request.form()
    user_text = (form.get("SpeechResult") or "").strip()

    if not user_text:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Please repeat your question.</Say>
    <Gather input="speech" action="{BASE_URL}/voice/process-speech" />
</Response>
"""

    lang_code, lang_key = detect_language(user_text)
    emotion = detect_emotion(user_text)

    # Load script safely
    script = {"intents": {}}
    if os.path.exists("data/script.json"):
        with open("data/script.json", encoding="utf-8") as f:
            script = json.load(f)

    intents = script.get("intents", {}).get(lang_key, {})
    fallback = intents.get("fallback", "Sorry, I did not understand.")
    reply = match_intent(user_text, intents, fallback)

    save_call_log("unknown", user_text, emotion)

    # END CALL
    if any(w in user_text.lower() for w in ["bye", "goodbye", "thanks"]):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{lang_code}">{reply}</Say>
    <Hangup/>
</Response>
"""

    audio = elevenlabs_tts(reply, emotion)
    if audio:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{BASE_URL}{audio}</Play>
    <Gather input="speech" action="{BASE_URL}/voice/process-speech" />
</Response>
"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{lang_code}">{reply}</Say>
    <Gather input="speech" action="{BASE_URL}/voice/process-speech" />
</Response>
"""
