# api/twilio_live_api.py

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from services.live_billing_service import live_deduct
from twilio.twiml.voice_response import VoiceResponse

router = APIRouter(prefix="/twilio-live", tags=["Twilio-Live"])

@router.post("/check", response_class=PlainTextResponse)
async def live_check(request: Request):
    form = await request.form()
    customer_id = form.get("CustomerId")

    vr = VoiceResponse()

    ok, balance = live_deduct(customer_id)

    if not ok:
        vr.say("Your balance is over. Call is ending.")
        vr.hangup()
        return str(vr)

    vr.pause(length=30)
    vr.redirect("/twilio-live/check")

    return str(vr)
