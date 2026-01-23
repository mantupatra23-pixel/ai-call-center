# api/billing_api.py

import json
from fastapi import APIRouter, Depends
from db.redis import redis_db
from core.auth_guard import get_current_user

router = APIRouter(prefix="/billing", tags=["Billing"])

# ===============================
# CUSTOMER – OWN BILLING HISTORY
# ===============================
@router.get("/my-history")
def my_billing_history(user=Depends(get_current_user)):
    customer_id = user["id"]
    logs = redis_db.lrange("billing:logs", 0, -1)

    result = []
    for log in logs:
        data = json.loads(log)
        if data["customer_id"] == customer_id:
            result.append(data)

    return {
        "customer_id": customer_id,
        "total_calls": len(result),
        "history": result
    }


# ===============================
# ADMIN – ALL BILLING HISTORY
# ===============================
@router.get("/all")
def all_billing():
    logs = redis_db.lrange("billing:logs", 0, -1)
    return [json.loads(l) for l in logs]
