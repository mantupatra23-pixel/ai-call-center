# api/wallet_api.py

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from services.wallet_service import (
    get_balance,
    add_balance,
    deduct_balance,
    has_sufficient_balance
)

from core.auth_guard import get_current_user, require_admin

router = APIRouter(prefix="/wallet", tags=["Wallet"])

# =====================
# MODELS
# =====================
class WalletUpdate(BaseModel):
    customer_id: str
    amount: float


# =====================
# CUSTOMER: VIEW OWN WALLET
# =====================
@router.get("/me")
def my_wallet(user=Depends(get_current_user)):
    return {
        "customer_id": user["id"],
        "balance": get_balance(user["id"]),
        "can_make_call": has_sufficient_balance(user["id"])
    }


# =====================
# ADMIN: VIEW ANY WALLET
# =====================
@router.get("/balance")
def wallet_balance(
    customer_id: str = Query(...),
    admin=Depends(require_admin)
):
    return {
        "customer_id": customer_id,
        "balance": get_balance(customer_id)
    }


# =====================
# ADMIN: ADD BALANCE
# =====================
@router.post("/admin/add")
def admin_add_balance(
    data: WalletUpdate,
    admin=Depends(require_admin)
):
    if data.amount <= 0:
        raise HTTPException(400, "Invalid amount")

    balance = add_balance(data.customer_id, data.amount)

    return {
        "status": "credited",
        "customer_id": data.customer_id,
        "balance": balance
    }


# =====================
# ADMIN: DEDUCT BALANCE
# =====================
@router.post("/admin/deduct")
def admin_deduct_balance(
    data: WalletUpdate,
    admin=Depends(require_admin)
):
    if data.amount <= 0:
        raise HTTPException(400, "Invalid amount")

    balance = deduct_balance(data.customer_id, data.amount)

    return {
        "status": "deducted",
        "customer_id": data.customer_id,
        "balance": balance
    }
