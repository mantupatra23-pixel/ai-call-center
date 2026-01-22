from fastapi import APIRouter
from db.redis import redis_db

router = APIRouter(prefix="/safety", tags=["Safety"])

# -------- ADMIN: BLOCK CUSTOMER --------
@router.post("/admin/block")
def admin_block(customer_id: str):
    redis_db.set(f"customer:{customer_id}:blocked", "1")
    return {"message": "Customer blocked"}

# -------- ADMIN: UNBLOCK CUSTOMER --------
@router.post("/admin/unblock")
def admin_unblock(customer_id: str):
    redis_db.delete(f"customer:{customer_id}:blocked")
    return {"message": "Customer unblocked"}
