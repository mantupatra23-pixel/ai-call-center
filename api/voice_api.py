import os
import json
import redis
from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from datetime import datetime
from groq import Groq

# =========================
# ROUTER
# =========================
router = APIRouter(prefix="/voice", tags=["Voice"])

# =========================
# ENV VARIABLES
# =========================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
BASE_URL = os.getenv("PUBLIC_BASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# =========================
# SAFE INIT (NO CRASH)
# =========================
twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
else:
    print("⚠️ Twilio not configured")

redis_conn = None
if REDIS_URL:
    try:
        redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        print("⚠️ Redis error:", e)

groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    print("⚠️ GROQ_API_KEY missing")

# =========================
# MEMORY FUNCTIONS
# =========================
def save_memory(call_sid, role, text):
    if not redis_conn:
        return
    try:
        redis_conn.rpush(f"call:{call_sid}", json.dumps({
            "role": role,
            "text": text
        }))
    except Exception as e:
        print("Memory save error:", e)

def get_memory(call_sid):
    if not redis_conn:
        return []
    try:
        data = redis_conn.lrange(f"call:{call_sid}", 0, -1)
        return [json.loads(x) for x in data]
    except:
        return []

# =========================
# AI REPLY (GROQ)
# =========================
def ai_reply(user_text: str, call_sid: str) -> str:
    if not groq_client:
        return "AI service abhi available nahi hai."

    history = get_memory(call_sid)

    messages = [
        {
            "role": "system",
            "content": "You are a Hindi AI call assistant. Speak short, polite and natural."
        }
    ]

    for h in history[-5:]:
        messages.append({
            "role": "assistant" if h["role"] == "AI" else "user",
            "content": h["text"]
        })

    messages.append({"role": "user", "content": user_text})

    try:
        res = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.5
        )
        reply = res.choices[0].message.content
    except Exception as e:
        print("AI ERROR:", e)
        reply = "System busy hai, please baad me try karein."

    save_memory(call_sid, "AI", reply)
    return reply

# =========================
# TWIML RESPONSE
# =========================
def get_txml(text):
    return f"""
<Response>
    <Say voice="Polly.Aditi" language="hi-IN">{text}</Say>
    <Gather input="speech" action="/voice/process" method="POST"/>
</Response>
"""

# =========================
# ROUTES
# =========================

@router.post("/start", response_class=PlainTextResponse)
async def start_call():
    msg = "Namaste! Main AI call assistant hoon. Aap kya jaanna chahte hain?"
    return get_txml(msg)

@router.post("/process", response_class=PlainTextResponse)
async def process(request: Request):
    form = await request.form()
    user_text = form.get("SpeechResult", "")
    call_sid = form.get("CallSid", "unknown")

    if not user_text:
        return get_txml("Mujhe sunai nahi diya, please dubara boliye.")

    save_memory(call_sid, "User", user_text)
    reply = ai_reply(user_text, call_sid)

    return get_txml(reply)

# =========================
# PLACE CALL FUNCTION
# =========================
def place_call(to: str, from_: str):
    if not twilio_client:
        print("❌ Twilio missing")
        return None

    if not BASE_URL:
        print("❌ PUBLIC_BASE_URL missing")
        return None

    try:
        call = twilio_client.calls.create(
            to=to,
            from_=from_,
            url=f"{BASE_URL}/voice/start"
        )
        return call.sid
    except Exception as e:
        print("CALL ERROR:", e)
        return None

# =========================
# TEST CALL API
# =========================
@router.get("/make-call")
def make_call(to: str = Query(...)):
    sid = place_call(to, TWILIO_NUMBER)
    if sid:
        return {"status": "success", "call_sid": sid}
    return {"status": "failed"}
