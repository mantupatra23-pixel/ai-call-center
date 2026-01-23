# api/admin_api.py

import os
import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from db.redis import redis_db
from services.active_call_service import list_active_calls

router = APIRouter(prefix="/admin", tags=["Admin"])

# =========================
# FILE PATHS
# =========================
LOG_PATH = "data/call_logs.json"

# =========================
# HELPERS
# =========================
def load_logs():
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

# =========================
# CALL LOGS & STATS
# =========================
@router.get("/calls")
def all_calls():
    return load_logs()

@router.get("/stats")
def stats():
    logs = load_logs()
    emotion_stats = {}

    for log in logs:
        emo = log.get("emotion", "unknown")
        emotion_stats[emo] = emotion_stats.get(emo, 0) + 1

    return {
        "total_calls": len(logs),
        "emotion_stats": emotion_stats
    }

# =========================
# LIVE CALLS (REAL-TIME)
# =========================
@router.get("/live-calls")
def live_calls():
    calls = list_active_calls()
    return {
        "active_calls": calls,
        "count": len(calls)
    }

# =========================
# CUSTOMER LISTING
# =========================
@router.get("/pending-customers")
def list_pending_customers():
    ids = redis_db.smembers("customers:pending")
    customers = []
    for cid in ids:
        data = redis_db.get(f"customer:{cid}")
        if data:
            customers.append(json.loads(data))
    return customers

@router.get("/approved-customers")
def list_approved_customers():
    ids = redis_db.smembers("customers:approved")
    customers = []
    for cid in ids:
        data = redis_db.get(f"customer:{cid}")
        if data:
            customers.append(json.loads(data))
    return customers

@router.get("/blocked-customers")
def list_blocked_customers():
    ids = redis_db.smembers("customers:blocked")
    customers = []
    for cid in ids:
        data = redis_db.get(f"customer:{cid}")
        if data:
            customers.append(json.loads(data))
    return customers

# =========================
# CUSTOMER ACTIONS
# =========================
@router.post("/approve-customer")
def approve_customer(customer_id: str = Query(...)):
    key = f"customer:{customer_id}"
    data = redis_db.get(key)
    if not data:
        raise HTTPException(404, "Customer not found")

    customer = json.loads(data)
    customer["status"] = "approved"

    redis_db.set(key, json.dumps(customer))
    redis_db.srem("customers:pending", customer_id)
    redis_db.sadd("customers:approved", customer_id)

    return {
        "message": "Customer approved",
        "customer_id": customer_id
    }

@router.post("/block-customer")
def block_customer(customer_id: str = Query(...)):
    key = f"customer:{customer_id}"
    data = redis_db.get(key)
    if not data:
        raise HTTPException(404, "Customer not found")

    customer = json.loads(data)
    customer["status"] = "blocked"

    redis_db.set(key, json.dumps(customer))
    redis_db.srem("customers:approved", customer_id)
    redis_db.sadd("customers:blocked", customer_id)

    return {
        "message": "Customer blocked",
        "customer_id": customer_id
    }

@router.post("/unblock-customer")
def unblock_customer(customer_id: str = Query(...)):
    key = f"customer:{customer_id}"
    data = redis_db.get(key)
    if not data:
        raise HTTPException(404, "Customer not found")

    customer = json.loads(data)
    customer["status"] = "approved"

    redis_db.set(key, json.dumps(customer))
    redis_db.srem("customers:blocked", customer_id)
    redis_db.sadd("customers:approved", customer_id)

    return {
        "message": "Customer unblocked",
        "customer_id": customer_id
    }

# =========================
# CALL RATE (ADMIN CONTROL)
# =========================
class RateRequest(BaseModel):
    call_rate_per_min: float

@router.post("/set-call-rate")
def set_call_rate(data: RateRequest):
    if data.call_rate_per_min <= 0:
        raise HTTPException(400, "Invalid rate")

    redis_db.set(
        "admin:config",
        json.dumps({
            "call_rate_per_min": data.call_rate_per_min
        })
    )

    return {
        "status": "rate_updated",
        "rate_per_min": data.call_rate_per_min
    }

@router.get("/get-call-rate")
def get_call_rate():
    raw = redis_db.get("admin:config")
    if not raw:
        return {"call_rate_per_min": 0}
    return json.loads(raw)

# =========================
# RECORDINGS
# =========================
@router.get("/recordings")
def all_recordings():
    logs = redis_db.lrange("recordings:all", 0, -1)
    return [json.loads(l) for l in logs]

# =========================
# HEALTH
# =========================
@router.get("/health")
def admin_health():
    return {"admin": "ok"}
