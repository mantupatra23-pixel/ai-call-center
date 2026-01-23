from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.redis import redis_db
import json

router = APIRouter(prefix="/admin/subscription", tags=["Admin-Subscription"])

class Plan(BaseModel):
    plan_id: str
    price: float
    minutes: int
    validity_days: int

@router.post("/set-plan")
def set_plan(plan: Plan):
    raw = redis_db.get("sub:plans")
    plans = json.loads(raw) if raw else {}

    plans[plan.plan_id] = plan.dict()
    redis_db.set("sub:plans", json.dumps(plans))

    return {"status": "plan_saved", "plan": plan.plan_id}
