from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from services.wallet_service import (
    get_balance,
    add_balance,
    deduct_balance,
    has_sufficient_balance
)

# --- INITIAL SETUP ---
# app.py handle karega "/wallet" prefix ko
router = APIRouter(tags=["Wallet"])

# --- MODELS ---
class WalletUpdate(BaseModel):
    customer_id: str
    amount: float

# --- PUBLIC/DASHBOARD ROUTES ---
# Ye frontend dialer aur dashboard ke liye hain

@router.get("/balance/{customer_id}")
async def wallet_balance(customer_id: str):
    """
    Frontend hits: GET /wallet/balance/mantu_admin
    """
    balance = get_balance(customer_id)
    return {
        "customer_id": customer_id,
        "balance": f"{float(balance):.2f}",
        "can_make_call": has_sufficient_balance(customer_id)
    }

@router.post("/add")
async def add_wallet_balance(data: WalletUpdate):
    """
    Frontend/Manual hit: POST /wallet/add
    """
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    new_balance = add_balance(data.customer_id, data.amount)
    return {
        "status": "credited",
        "customer_id": data.customer_id,
        "balance": new_balance
    }

# --- AUTH PROTECTED ROUTES (Optional/Future use) ---

@router.get("/me")
def my_wallet(customer_id: str = "mantu_admin"):
    # Abhi ke liye hardcoded ya simple query rakha hai taaki crash na ho
    return {
        "customer_id": customer_id,
        "balance": get_balance(customer_id)
    }

@router.post("/deduct")
async def manual_deduct(data: WalletUpdate):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    new_balance = deduct_balance(data.customer_id, data.amount)
    return {
        "status": "deducted",
        "customer_id": data.customer_id,
        "balance": new_balance
    }
