import os
from fastapi import APIRouter
from twilio.rest import Client

router = APIRouter()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_FROM      = os.getenv("TWILIO_WHATSAPP_FROM")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp(to_phone: str, text: str):
    client.messages.create(
        from_=WHATSAPP_FROM,
        to=f"whatsapp:{to_phone}",
        body=text
    )
