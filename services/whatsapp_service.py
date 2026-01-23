# services/whatsapp_service.py

import os
from twilio.rest import Client

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
WHATSAPP_FROM = "whatsapp:+14155238886"  # Twilio sandbox / approved number

client = Client(TWILIO_SID, TWILIO_TOKEN)

def send_whatsapp(to_phone: str, text: str):
    client.messages.create(
        from_=WHATSAPP_FROM,
        to=f"whatsapp:{to_phone}",
        body=text
    )
