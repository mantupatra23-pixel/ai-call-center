import os
from twilio.rest import Client

# FIXED: Ab ye Render dashboard wale exact naam use karega
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")

# SAFE CHECK: Agar keys nahi milti toh server crash nahi hoga, sirf warning aayegi
if not TWILIO_SID or not TWILIO_TOKEN:
    print("⚠️ Warning: Twilio credentials missing in twilio_numbers.py")
    twilio_client = None
else:
    twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

def buy_number(country: str):
    """
    country: "US" | "IN" | "AE" (example)
    NOTE: Twilio availability varies by country.
    """
    if not twilio_client:
        raise RuntimeError("Twilio API keys missing, cannot buy number")

    search_kwargs = {}
    if country == "US":
        search_kwargs = {"sms_enabled": True}
    elif country == "IN":
        search_kwargs = {"voice_enabled": True}
    else:
        search_kwargs = {"voice_enabled": True}

    # API request to find available number
    numbers = twilio_client.available_phone_numbers(country).local.list(**search_kwargs, limit=1)
    
    if not numbers:
        raise RuntimeError("No numbers available")

    # Buy the number
    purchased = twilio_client.incoming_phone_numbers.create(
        phone_number=numbers[0].phone_number
    )
    return purchased.phone_number
