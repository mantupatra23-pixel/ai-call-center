import os
import requests

# --- CONFIG ---
VAPI_API_KEY = os.getenv("VAPI_API_KEY")

def buy_vapi_number(area_code: str = "91", name: str = "Primary_Business_Line"):
    """
    Vapi/Telnyx ke zariye naya number purchase karne ka logic.
    """
    if not VAPI_API_KEY:
        print("⚠️ Warning: VAPI_API_KEY missing. Number purchase disabled.")
        return None

    url = "https://api.vapi.ai/phone-number"
    
    # Vapi Number Purchase Payload
    payload = {
        "provider": "vapi", # Aap yahan 'telnyx' ya 'twilio' bhi specify kar sakte hain agar linked hai
        "name": name,
        "areaCode": area_code
    }
    
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            data = response.json()
            # Redis mein naya number save kar lo tracking ke liye
            from db.redis import redis_db
            redis_db.set(f"number:active:{data.get('id')}", data.get('number'))
            
            return data.get("number")
        else:
            print(f"Vapi Number Purchase Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Critical Number Service Error: {e}")
        return None

def list_active_numbers():
    """
    System mein jitne active numbers hain unki list nikalne ke liye.
    """
    url = "https://api.vapi.ai/phone-number"
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
    
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else []
