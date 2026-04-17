import os
from fastapi import APIRouter, Request, HTTPException
from services.live_billing_service import live_deduct
from db.redis import redis_db

# Naya Router Setup
router = APIRouter(prefix="/vapi-live", tags=["Vapi-Live"])

@router.post("/balance-check")
async def vapi_balance_check(request: Request):
    """
    Vapi Call ke beech mein balance check karne ke liye logic.
    """
    data = await request.json()
    customer_id = data.get("customer", {}).get("name") # Metadata se ID uthayega

    if not customer_id:
        return {"status": "error", "message": "Customer ID missing"}

    # Live balance deduct aur check logic
    ok, balance = live_deduct(customer_id)

    if not ok:
        # Agar balance khatam ho jaye, toh Vapi ko call end karne ka signal bhejenge
        return {
            "results": [
                {
                    "toolCallId": data.get("toolCallId"),
                    "result": "Your balance is over. The call is ending now.",
                    "endCall": True
                }
            ]
        }

    return {"status": "ok", "remaining_balance": balance}

@router.post("/webhook")
async def vapi_status_webhook(request: Request):
    """
    Call status update handle karne ke liye.
    """
    data = await request.json()
    print(f"Vapi Live Status: {data.get('type')}")
    return {"status": "received"}
