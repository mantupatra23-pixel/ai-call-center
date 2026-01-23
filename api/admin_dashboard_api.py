# api/admin_dashboard_api.py

from fastapi import APIRouter
from core.auth_guard import get_current_user
from fastapi import Depends

from services.revenue_service import (
    revenue_summary,
    revenue_today,
    revenue_month,
    customer_wise_revenue,
    plan_sales
)

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin-Dashboard"]
)

# =========================
# OVERALL SUMMARY
# =========================
@router.get("/summary")
def summary():
    """
    Wallet + Subscription + Total revenue
    """
    return revenue_summary()


# =========================
# TODAY REVENUE
# =========================
@router.get("/today")
def today():
    return {
        "today_revenue": revenue_today()
    }


# =========================
# MONTH REVENUE
# =========================
@router.get("/month")
def month():
    return {
        "month_revenue": revenue_month()
    }


# =========================
# CUSTOMER WISE REVENUE
# =========================
@router.get("/customers")
def customers():
    """
    Per customer earning breakdown
    """
    return customer_wise_revenue()


# =========================
# SUBSCRIPTION PLAN SALES
# =========================
@router.get("/plans")
def plans():
    """
    Plan-wise subscription sales
    """
    return plan_sales()
