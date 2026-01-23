from services.call_registry_service import register_call_start

call = twilio_client.calls.create(
    to=to_phone,
    from_=from_phone,
    url=f"{BASE_URL}/voice/twilio-voice",
    record=True
)

register_call_start(customer_id, call.sid)
