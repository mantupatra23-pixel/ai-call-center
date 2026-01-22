from fastapi import APIRouter, Depends
from services.analytics_service import (
    customer_daily_metrics,
    customer_monthly_metrics,
    admin_overview
)
from core.deps import get_current_user, admin_only

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# -------- CUSTOMER: DAILY --------
@router.get("/customer/daily")
def my_daily(user=Depends(get_current_user)):
    return customer_daily_metrics(user["user_id"])

# -------- CUSTOMER: MONTHLY --------
@router.get("/customer/monthly")
def my_monthly(user=Depends(get_current_user)):
    return customer_monthly_metrics(user["user_id"])

# -------- ADMIN: OVERVIEW --------
@router.get("/admin/overview")
def overview(user=Depends(admin_only)):
    return admin_overview()
