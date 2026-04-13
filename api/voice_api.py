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

# Project Imports (Ensure these paths exist in your repo)
from db.redis import redis_db
from core.auth_guard import get_current_user
from services.ai_agent_service import ai_reply
from services.ai_memory_service import (
    add_call_memory, get_call_memory, increment_call_count, should_summarize, save_summary
)
from services.billing_service import start_call_billing, stop_call_billing
from services.crm_service import create_lead
from services.whatsapp_service import send_whatsapp
from services.sales_service import detect_sales_intent, upsell_reply
from services.booking_service import save_booking

# =================================================================
# CONFIGURATION & CLIENTS
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
# AZURE NEURAL TTS ENGINE
# =================================================================
def generate_voice(text: str) -> str:
    """Generates high-quality human-like voice using Azure Neural TTS."""
    voice_dir = "static/voice"
    os.makedirs(voice_dir, exist_ok=True)
    
    # Cleanup: Delete files older than 1 hour to save space
    for f in os.listdir(voice_dir):
        fpath = os.path.join(voice_dir, f)
        if os.path.getmtime(fpath) < (datetime.now() - timedelta(hours=1)).timestamp():
            os.remove(fpath)

    fname = f"v_{abs(hash(text))}.mp3"
    path = f"{voice_dir}/{fname}"
    full_path = os.path.join(os.getcwd(), path)

    if not os.path.exists(full_path):
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=full_path)
        # Professional Indian Male Voice
        speech_config.speech_synthesis_voice_name = "hi-IN-MadhurNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        # SSML for "Real Human" Expression
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='hi-IN'>
            <voice name='hi-IN-MadhurNeural'>
                <mstts:express-as style='cheerful' styledegree='1.2'>
                    <prosody rate='-3%'>
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        synthesizer.speak_ssml_async(ssml).get()

    return f"{BASE_URL}/{path}"

# =================================================================
# TWILIO TXML GENERATOR
# =================================================================
def txml_response(audio_url: str, gathering: bool = True):
    """Generates TXML with Barge-in and Background Ambience support."""
    response = f'<?xml version="1.0" encoding="UTF-8"?><Response>'
    # Background noise (Make sure this file exists in your static folder)
    # response += f'<Play loop="0">{BASE_URL}/static/office_ambience.mp3</Play>'
    
    response += f'<Play>{audio_url}</Play>'
    
    if gathering:
        response += f'''<Gather 
            input="speech" 
            timeout="5" 
            action="{BASE_URL}/voice/process-speech" 
            method="POST" 
            speechTimeout="auto" 
            hints="hello, price, interest, manager"
            interruptible="true"
        />'''
        response += f'<Redirect>{BASE_URL}/voice/process-speech</Redirect>' # Fallback if no speech
    
    response += '</Response>'
    return response

# =================================================================
# ENDPOINTS
# =================================================================

@router.post("/make-call")
def make_call(to_phone: str = Query(...), from_phone: str = Query(...), user=Depends(get_current_user)):
    """Triggers an outbound call via RQ Worker."""
    if not to_phone.startswith("+"):
        raise HTTPException(400, "Invalid phone format. Use E.164")
    
    # Simple Wallet Check (Logic from your models)
    if user.get("wallet", 0) <= 0:
        raise HTTPException(402, "Insufficient Balance")
    
    job = call_queue.enqueue(place_call, to_phone, from_phone, user["id"])
    return {"status": "queued", "job_id": job.id}

@router.post("/twilio-voice", response_class=PlainTextResponse)
async def twilio_voice(request: Request):
    """Initial Greeting with Answering Machine Detection."""
    form = await request.form()
    answered_by = form.get("AnsweredBy", "human")

    # If Voicemail/Machine detected, hang up to save money
    if "machine" in answered_by.lower():
        return "<Response><Hangup/></Response>"

    msg = "Namaskar! Main Visora AI se baat kar raha hoon. Kya main aapka do minute le sakta hoon?"
    return txml_response(generate_voice(msg))

@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    """Core logic for AI Conversation, Sales Intent, and Memory."""
    form = await request.form()
    call_sid = form.get("CallSid")
    text = (form.get("SpeechResult") or "").strip()
    to_phone = form.get("To")
    customer_id = redis_db.get(f"call:customer:{call_sid}")

    # 1. Handle Silence
    if not text:
        return txml_response(generate_voice("Maaf kijiye, main sun nahi paaya. Kripya phir se bolein."))

    # 2. Human Handoff / Manager Request
    if any(w in text.lower() for w in ["manager", "senior", "insaan", "human"]):
        audio = generate_voice("Zaroor, main hamare senior manager ko call transfer kar raha hoon. Kripya line par bane rahein.")
        return f'<Response><Play>{audio}</Play><Dial>+91YOUR_REAL_NUMBER</Dial></Response>'

    # 3. Call Termination
    if any(w in text.lower() for w in ["bye", "cut", "shukriya", "no thanks"]):
        return f'<Response><Play>{generate_voice("Theek hai, dhanyavaad.")}</Play><Hangup/></Response>'

    # 4. AI Thinking & Memory
    add_call_memory(call_sid, "User", text)
    history = get_call_memory(call_sid)
    
    # Load Business Context
    try:
        with open("data/company_profile.json") as f:
            profile = json.load(f)
    except:
        profile = {"name": "Visora AI", "service": "Automation"}

    intent = detect_sales_intent(text)
    
    # Sales Upsell Logic
    reply = upsell_reply(intent)
    if not reply:
        reply = ai_reply(user_text=text, history=history, company_profile=profile, lang="hi")

    add_call_memory(call_sid, "AI", reply)

    # 5. Lead & Booking Actions
    if intent in ["booking", "buy", "interested"]:
        save_booking(call_sid=call_sid, phone=to_phone)
        create_lead(call_sid=call_sid, phone=to_phone, intent=intent)

    return txml_response(generate_voice(reply))

@router.post("/call-status")
async def call_status(request: Request):
    """Handles Billing and Post-Call Automations."""
    form = await request.form()
    sid = form.get("CallSid")
    status = form.get("CallStatus")
    to_phone = form.get("To")

    if status in ["completed", "failed"]:
        cid = redis_db.get(f"call:customer:{sid}")
        stop_call_billing(sid, cid)
        
        if status == "completed":
            send_whatsapp(to_phone, "Visora AI se baat karne ke liye shukriya! Hum jald hi aapse sampark karenge.")
            
    return {"status": "tracked"}

# =================================================================
# WORKER FUNCTION (Twilio Outbound)
# =================================================================
def place_call(to_phone: str, from_phone: str, customer_id: str):
    """The function executed by RQ Worker to trigger the call."""
    try:
        call = twilio_client.calls.create(
            machine_detection='Enable',
            async_amd='true',
            to=to_phone,
            from=from_phone,
            url=f"{BASE_URL}/voice/twilio-voice",
            status_callback=f"{BASE_URL}/voice/call-status",
            status_callback_event=["completed"]
        )
        redis_db.set(f"call:customer:{call.sid}", customer_id)
        start_call_billing(call.sid, customer_id)
    except TwilioRestException as e:
        print(f"Twilio API Error: {e}")
