import os
import requests

# --- ENV LOADING ---
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL") # Meta/Generic API URL
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")     # API Bearer Token
WHATSAPP_FROM_NUMBER_ID = os.getenv("WHATSAPP_FROM_NUMBER_ID")

def send_whatsapp(to_phone: str, text: str):
    """
    Twilio Bypass: Seedha WhatsApp Business API (Meta/Cloud) ke zariye message bhejega.
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_API_URL:
        print("⚠️ WhatsApp Credentials missing in Env. Skipping message.")
        return False

    # Standard Meta/Cloud API Payload Format
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
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
        if response.status_code == 200:
            print(f"✅ WhatsApp sent to {to_phone}")
            return True
        else:
            print(f"❌ WhatsApp Error: {response.text}")
            return False
    except Exception as e:
        print(f"Critical WhatsApp Service Error: {e}")
        return False
