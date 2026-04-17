import os
import requests
from services.call_registry_service import register_call_start

# --- ENV LOADING ---
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")

def place_call(to_phone: str, from_number: str, customer_id: str):
    """
    Twilio Bypass: Ab ye seedha Vapi API ko hit karega.
    Function name wahi rakha hai taaki baki files mein error na aaye.
    """
    if not VAPI_API_KEY or not VAPI_ASSISTANT_ID:
        print("⚠️ Vapi Config Missing in services/voice_api.py")
        return None

    url = "https://api.vapi.ai/call/phone"
    
    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "customer": {
            "number": to_phone,
            "name": customer_id
        },
        "metadata": {
            "customer_id": customer_id,
            "original_from": from_number
        }
    }
    
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            call_data = response.json()
            call_id = call_data.get("id")
            
            # Aapka existing registry logic
            register_call_start(customer_id, call_id)
            
            print(f"✅ Vapi Call Started: {call_id}")
            return call_id
        else:
            print(f"❌ Vapi API Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Critical Error in place_call: {e}")
        return None
