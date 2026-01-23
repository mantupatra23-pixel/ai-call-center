# api/subscription_api.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import time

from core.auth_guard import get_current_user
from services.subscription_service import (
    activate_plan,
    get_subscription,
    is_subscription_active,
    get_plans,
    set_plans
)

router = APIRouter(prefix="/subscription", tags=["Subscription"])


# =========================
# MODELS
# =========================

class PlanActivate(BaseModel):
    plan_id: str
    auto_renew: bool = True


class PlansUpdate(BaseModel):
    plans: dict


# =========================
# ADMIN APIs
# =========================

@router.post("/admin/set-plans")
def admin_set_plans(data: PlansUpdate):
    """
    Admin dynamically sets plans in Redis
    """
    if not isinstance(data.plans, dict):
        raise HTTPException(400, "Invalid plans format")

    set_plans(data.plans)

    return {
        "status": "plans_updated",
        "plans": data.plans
    }


@router.get("/admin/plans")
def admin_get_plans():
    """
    Admin view all plans
    """
    return get_plans()


# =========================
# CUSTOMER APIs
# =========================

@router.get("/plans")
def list_plans():
    """
    Public endpoint → show plans to users
    """
    plans = get_plans()
    if not plans:
        raise HTTPException(404, "No plans available")
    return plans


@router.post("/activate")
def activate_subscription(
    data: PlanActivate,
    user=Depends(get_current_user)
):
    """
    Activate a subscription plan for user
    """
    ok = activate_plan(
        customer_id=user["id"],
        plan_id=data.plan_id,
        auto_renew=data.auto_renew
    )

    if not ok:
        raise HTTPException(400, "Invalid or expired plan")

    return {
        "status": "subscription_activated",
        "plan_id": data.plan_id,
        "auto_renew": data.auto_renew
    }


@router.get("/my")
def my_subscription(user=Depends(get_current_user)):
    """
    Get current user's subscription
    """
    sub = get_subscription(user["id"])
    if not sub:
        return {
            "active": False,
            "subscription": None
        }

    return {
        "active": is_subscription_active(user["id"]),
        "subscription": sub
    }
