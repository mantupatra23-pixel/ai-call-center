import json, os
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()
LEAD_FILE = "data/leads.json"

def save_lead(data):
    os.makedirs("data", exist_ok=True)
    with open(LEAD_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")


@router.post("/save-lead")
def save_lead_api(
    call_sid: str,
    phone: str,
    intent: str,
    language: str,
    message: str
):
    status = "cold"
    if intent in ["price", "booking", "demo"]:
        status = "hot"
    elif intent in ["info", "features"]:
        status = "warm"

    data = {
        "call_sid": call_sid,
        "phone": phone,
        "intent": intent,
        "status": status,
        "language": language,
        "last_message": message,
        "timestamp": datetime.utcnow().isoformat()
    }

    save_lead(data)
    return {"status": "lead saved", "lead_type": status}
