import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

# --- ENV LOADING ---
# Ab hum Twilio ki jagah naya provider use karenge
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL") # E.g., Meta ya AiSensy ka URL
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")

class WhatsAppRequest(BaseModel):
    to_phone: str
    message: str

def send_whatsapp_msg(to_phone: str, text: str):
    """
    Twilio Bypass: Standard HTTP Request ke zariye WhatsApp bhejega.
    """
    if not WHATSAPP_TOKEN:
        print("⚠️ WhatsApp Token missing. Message not sent.")
        return False

    # Example payload for Meta/Generic API
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text}
    }
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"WhatsApp Error: {e}")
        return False

@router.post("/send")
async def send_message(data: WhatsAppRequest):
    """
    API Endpoint to send WhatsApp from Dashboard
    """
    success = send_whatsapp_msg(data.to_phone, data.message)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send WhatsApp message")
    
    return {"status": "success", "message": "WhatsApp sent successfully"}
