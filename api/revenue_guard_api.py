from fastapi import APIRouter
from db.redis import redis_db

router = APIRouter(prefix="/admin/revenue", tags=["Revenue"])

@router.get("/low-balance-alerts")
def low_balance_alerts():
    return redis_db.lrange("alerts:low_balance", 0, 50)
