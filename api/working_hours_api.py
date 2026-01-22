from fastapi import APIRouter, Depends
from services.working_hours_service import set_hours
from core.deps import get_current_user

router = APIRouter(prefix="/hours", tags=["WorkingHours"])

@router.post("/set")
def set_working_hours(start: int, end: int, tz: str, user=Depends(get_current_user)):
    set_hours(user["user_id"], start, end, tz)
    return {"message": "Working hours set"}
