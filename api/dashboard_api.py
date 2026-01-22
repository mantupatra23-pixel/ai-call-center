import os
import json
from fastapi import APIRouter, HTTPException

from db.redis import redis_db

# =====================================
# ROUTER
# =====================================
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# =====================================
# FILE PATH
# =====================================
DATA_PATH = "data/call_logs.json"

# =====================================
# DASHBOARD STATS
# =====================================
@router.get("/stats")
def dashboard_stats():
    if not os.path.exists(DATA_PATH):
        return {
            "total_calls": 0,
            "emotion_breakdown": {},
            "recent_calls": []
        }

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    emotions = {}
    for c in data:
        emo = c.get("emotion", "unknown")
        emotions[emo] = emotions.get(emo, 0) + 1

    return {
        "total_calls": len(data),
        "emotion_breakdown": emotions,
        "recent_calls": data[-20:]
    }

# =====================================
# CUSTOMER: SELECT ACTIVE NUMBER
# =====================================
@router.post("/select-number")
def select_number(customer_id: str, phone_number: str):
    raw = redis_db.get(f"number:{phone_number}")
    if not raw:
        raise HTTPException(status_code=404, detail="Number not found")

    num = json.loads(raw)

    if num.get("status") != "active" or num.get("customer_id") != customer_id:
        raise HTTPException(
            status_code=400,
            detail="Number not active for this customer"
        )

    redis_db.set(f"customer:{customer_id}:selected_number", phone_number)

    return {
        "message": "Number selected successfully",
        "phone_number": phone_number
    }

# =====================================
# CUSTOMER: GET SELECTED NUMBER
# =====================================
@router.get("/selected-number/{customer_id}")
def get_selected_number(customer_id: str):
    phone = redis_db.get(f"customer:{customer_id}:selected_number")
    return {
        "customer_id": customer_id,
        "selected_number": phone
    }
