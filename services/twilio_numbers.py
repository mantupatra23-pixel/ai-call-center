import os
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    raise RuntimeError("Twilio credentials missing")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def buy_number(country: str):
    """
    country: 'US' | 'IN' | 'AE' (example)
    NOTE: Twilio availability varies by country.
    """
    search_kwargs = {}
    if country == "US":
        search_kwargs = {"country": "US", "sms_enabled": True, "voice_enabled": True}
    elif country == "IN":
        search_kwargs = {"country": "IN", "voice_enabled": True}
    else:
        search_kwargs = {"country": "US", "voice_enabled": True}

    numbers = twilio_client.available_phone_numbers(**search_kwargs).local.list(limit=1)
    if not numbers:
        raise RuntimeError("No numbers available")

    purchased = twilio_client.incoming_phone_numbers.create(
        phone_number=numbers[0].phone_number
    )
    return purchased.phone_number
