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
    add_call_memory, get_call_memory, increment_call_count, should_summarize, save_summary
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
# AZURE NEURAL TTS (PRO VERSION)
# =================================================================
def generate_voice(text: str) -> str:
    """Generates high-fidelity human-like voice and manages cleanup."""
    voice_dir = "static/voice"
    os.makedirs(voice_dir, exist_ok=True)
    
    # Auto-cleanup files older than 30 mins to avoid Render storage limits
    for f in os.listdir(voice_dir):
        fpath = os.path.join(voice_dir, f)
        if os.path.getmtime(fpath) < (datetime.now() - timedelta(minutes=30)).timestamp():
            try: os.remove(fpath)
            except: pass

    fname = f"v_{abs(hash(text))}.mp3"
    path = f"{voice_dir}/{fname}"
    full_path = os.path.join(os.getcwd(), path)

    if not os.path.exists(full_path):
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=full_path)
        
        # Best Indian Professional Voice
        speech_config.speech_synthesis_voice_name = "hi-IN-MadhurNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        # SSML: Cheerful style for sales conversion
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='hi-IN'>
            <voice name='hi-IN-MadhurNeural'>
                <mstts:express-as style='cheerful' styledegree='1.1'>
                    <prosody rate='-2%'>
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        synthesizer.speak_ssml_async(ssml).get()

    return f"{BASE_URL}/{path}"

# =================================================================
# TWILIO RESPONSE GENERATOR
# =================================================================
def get_txml(audio_url: str, gather: bool = True):
    """Twilio Markup with Barge-in (Interruption) support."""
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response>'
    xml += f'<Play>{audio_url}</Play>'
    
    if gather:
        xml += f'''<Gather 
            input="speech" 
            timeout="4" 
            action="{BASE_URL}/voice/process-speech" 
            method="POST" 
            speechTimeout="auto" 
            hints="haan, price, interested, callback"
            interruptible="true"
        />'''
        # Fallback if user stays silent
        xml += f'<Redirect>{BASE_URL}/voice/process-speech</Redirect>'
    
    xml += '</Response>'
    return xml

# =================================================================
# API ENDPOINTS
# =================================================================

@router.post("/make-call")
def make_call(to_phone: str = Query(...), from_phone: str = Query(...), user=Depends(get_current_user)):
    """Triggers call through Redis Worker."""
    if not to_phone.startswith("+"):
        raise HTTPException(400, "Phone number must be in E.164 format (e.g. +91...)")
    
    # Wallet Balance Check
    if user.get("wallet", 0) <= 0:
        raise HTTPException(402, "Low Wallet Balance. Please Recharge.")
    
    job = call_queue.enqueue(place_call, to_phone, from_phone, user["id"])
    return {"status": "success", "message": "Call Queued", "job_id": job.id}

@router.post("/twilio-voice", response_class=PlainTextResponse)
async def twilio_voice(request: Request):
    """Entry point for Twilio Calls with AMD."""
    form = await request.form()
    # Check if a machine (voicemail) answered
    if "machine" in form.get("AnsweredBy", "human").lower():
        return "<Response><Hangup/></Response>"

    welcome_msg = "Namaskar! Main Visora AI se baat kar raha hoon. Kya main aapka thoda samay le sakta hoon?"
    return get_txml(generate_voice(welcome_msg))

@router.post("/process-speech", response_class=PlainTextResponse)
async def process_speech(request: Request):
    """Main Conversation Loop & Sales Logic."""
    form = await request.form()
    call_sid = form.get("CallSid")
    text = (form.get("SpeechResult") or "").strip()
    to_phone = form.get("To")
    customer_id = redis_db.get(f"call:customer:{call_sid}")

    # Handle silence
    if not text:
        return get_txml(generate_voice("Maaf kijiye, mujhe sunayi nahi diya. Kya aap phir se bol sakte hain?"))

    # Human Transfer (Elite Feature)
    if any(w in text.lower() for w in ["manager", "senior", "human", "insaan"]):
        transfer_msg = "Zaroor, main aapki call hamare senior manager ko transfer kar raha hoon. Kripya bane rahein."
        return f'<Response><Play>{generate_voice(transfer_msg)}</Play><Dial>+919876543210</Dial></Response>'

    # Termination Logic
    if any(w in text.lower() for w in ["bye", "band", "no thanks", "shukriya"]):
        return f'<Response><Play>{generate_voice("Dhanyavaad, aapka din shubh ho.")}</Play><Hangup/></Response>'

    # AI Brain Execution
    add_call_memory(call_sid, "User", text)
    history = get_call_memory(call_sid)
    
    intent = detect_sales_intent(text)
    reply = upsell_reply(intent)
    
    if not reply:
        try:
            with open("data/company_profile.json") as f:
                profile = json.load(f)
        except:
            profile = {"name": "Visora AI"}
        reply = ai_reply(user_text=text, history=history, company_profile=profile, lang="hi")

    add_call_memory(call_sid, "AI", reply)

    # Automated Lead Gen
    if intent in ["booking", "interested", "price"]:
        save_booking(call_sid=call_sid, phone=to_phone)
        create_lead(call_sid=call_sid, phone=to_phone, intent=intent)

    return get_txml(generate_voice(reply))

@router.post("/call-status")
async def call_status(request: Request):
    """Finalizing Billing & Automations after call ends."""
    form = await request.form()
    sid = form.get("CallSid")
    status = form.get("CallStatus")
    to_phone = form.get("To")

    if status in ["completed", "failed"]:
        cid = redis_db.get(f"call:customer:{sid}")
        stop_call_billing(sid, cid)
        
        if status == "completed":
            # Post-call followup
            send_whatsapp(to_phone, "Thanks for talking to Visora AI! We have saved your request.")
            
    return {"status": "processed"}

# =================================================================
# WORKER LOGIC
# =================================================================
def place_call(to_phone: str, from_phone: str, customer_id: str):
    """Executed by Redis Worker."""
    try:
        call = twilio_client.calls.create(
            machine_detection='Enable', # AMD Enabled
            async_amd='true',
            to=to_phone,
            from=from_phone,
            url=f"{BASE_URL}/voice/twilio-voice",
            status_callback=f"{BASE_URL}/voice/call-status",
            status_callback_event=["completed"]
        )
        # Link SID to User for billing
        redis_db.set(f"call:customer:{call.sid}", customer_id)
        start_call_billing(call.sid, customer_id)
    except TwilioRestException as e:
        print(f"Twilio API Error: {e}")
