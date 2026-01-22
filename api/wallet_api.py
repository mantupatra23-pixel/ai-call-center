from fastapi import APIRouter, HTTPException
from services.wallet_service import (
    get_balance, add_balance
)

router = APIRouter(prefix="/wallet", tags=["Wallet"])

# -------- CUSTOMER: VIEW BALANCE --------
@router.get("/{customer_id}")
def wallet_balance(customer_id: str):
    return {
        "customer_id": customer_id,
        "balance": get_balance(customer_id)
    }

# -------- ADMIN: ADD BALANCE --------
@router.post("/admin/add")
def admin_add_balance(customer_id: str, amount: float):
    if amount <= 0:
        raise HTTPException(400, "Invalid amount")

    add_balance(customer_id, amount)

    return {
        "message": "Wallet recharged",
        "customer_id": customer_id,
        "balance": get_balance(customer_id)
    }
