import os, json, redis, requests
from rq import Queue
from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse
from twilio.rest import Client

from api.whatsapp_api import send_whatsapp

router = APIRouter()

# ================= ENV =================
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE       = os.getenv("TWILIO_PHONE")
BASE_URL           = os.getenv("PUBLIC_BASE_URL")

REDIS_HOST         = os.getenv("REDIS_HOST")
REDIS_PASSWORD     = os.getenv("REDIS_PASSWORD")

ELEVEN_API_KEY     = os.getenv("ELEVEN_API_KEY")
ELEVEN_VOICE_ID    = os.getenv("ELEVEN_VOICE_ID")

# ================= CLIENTS =================
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

redis_conn = redis.Redis(
    host=REDIS_HOST,
    port=6379,
    password=REDIS_PASSWORD,
    decode_responses=True
)

call_queue = Queue("calls", connection=redis_conn)

# ================= HELPERS =================
def detect_language(text: str):
    text = text.lower()
    if any("\u0600" <= c <= "\u06FF" for c in text):
        return "ar-SA", "arabic"
    if any(w in text for w in ["kya", "hai", "rupaye", "price"]):
        return "hi-IN", "hindi"
    return "en-US", "english"

def detect_emotion(text: str):
    text = text.lower()
    if any(w in text for w in ["problem", "complaint", "bekar", "issue"]):
        return "angry"
    if any(w in text for w in ["thank", "thanks", "great", "good"]):
        return "happy"
    if any(w in text for w in ["sad", "bad", "disappointed"]):
        return "sad"
    return "neutral"

def match_intent(text: str, intents: dict, fallback: str):
    text = text.lower()
    for key, reply in intents.items():
        if key != "fallback" and key in text:
            return reply
    return fallback

def save_call_log(phone, text, emotion):
    os.makedirs("data", exist_ok=True)
    path = "data/call_logs.json"
    data = []
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)

    data.append({
        "phone": phone,
        "text": text,
        "emotion": emotion
    })

    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def elevenlabs_tts(text: str, emotion="neutral"):
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

    r = requests.post(url, json=payload, headers=headers)
    os.makedirs("voice", exist_ok=True)
    audio_path = "voice/output.mp3"

    with open(audio_path, "wb") as f:
        f.write(r.content)

    return audio_path

def followup_message(emotion):
    if emotion == "angry":
        return "Sorry for inconvenience 🙏 Our senior agent will call you shortly."
    if emotion == "happy":
        return "Thank you 😊 Here is our offer: https://pay.link/demo"
    if emotion == "sad":
        return "We understand. Please tell us how we can help you better."
    return "Thanks for calling! Need anything else?"

# ================= WORKER =================
def place_call(phone: str):
    twilio_client.calls.create(
        to=phone,
        from_=TWILIO_PHONE,
        url=f"{BASE_URL}/twilio-voice",
        record=True
    )

# ================= API =================
@router.post("/make-call")
def make_call(phone: str = Query(...)):
    job = call_queue.enqueue(place_call, phone)
    return {"queued": True, "job_id": job.id, "phone": phone}

@router.post("/twilio-voice", response_class=PlainTextResponse)
def twilio_voice():
    return f"""
<Response>
    <Say language="hi-IN">Namaskar! Hello! Marhaban!</Say>
    <Gather input="speech" action="{BASE_URL}/process-speech"/>
</Response>
"""

@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    form = await request.form()
    user_text = (form.get("SpeechResult") or "").strip()

    lang_code, lang_key = detect_language(user_text)
    emotion = detect_emotion(user_text)

    with open("data/script.json", encoding="utf-8") as f:
        script = json.load(f)

    intents = script.get("intents", {}).get(lang_key, {})
    fallback = intents.get("fallback", "Sorry, I did not understand.")
    reply = match_intent(user_text, intents, fallback)

    save_call_log("unknown", user_text, emotion)

    audio = elevenlabs_tts(reply, emotion)

    # WhatsApp follow-up
    send_whatsapp(
        to_phone="91XXXXXXXXXX",   # paid account me real caller number
        text=followup_message(emotion)
    )

    if any(w in user_text.lower() for w in ["bye", "thanks"]):
        return f"""
<Response>
    <Play>{BASE_URL}/{audio}</Play>
    <Hangup/>
</Response>
"""

    return f"""
<Response>
    <Play>{BASE_URL}/{audio}</Play>
    <Gather input="speech" action="{BASE_URL}/process-speech"/>
</Response>
"""
