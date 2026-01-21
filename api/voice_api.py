import os
from fastapi import APIRouter, Query
from twilio.rest import Client
from fastapi.responses import PlainTextResponse

router = APIRouter()

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@router.post("/make-call")
def make_call(phone: str = Query(...)):
    call = client.calls.create(
        to=phone,
        from_=TWILIO_PHONE,
        url="https://ai-call-center-x1df.onrender.com/twilio-voice"
    )
    return {"status": "calling", "sid": call.sid}


@router.post("/twilio-voice", response_class=PlainTextResponse)
def twilio_voice():
    return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="hi-IN">
    Namaskar! Main AI call center bol raha hoon. 
    Hamari service 499 rupaye se shuru hoti hai.
    Dhanyavaad!
  </Say>
</Response>
"""
