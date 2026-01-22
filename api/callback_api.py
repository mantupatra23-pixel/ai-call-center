from fastapi import APIRouter, Depends
from services.callback_service import schedule_callback
from core.deps import get_current_user
import time

router = APIRouter(prefix="/callback", tags=["Callback"])

@router.post("/schedule")
def schedule(to_phone: str, minutes_after: int = 1440, user=Depends(get_current_user)):
    when = int(time.time()) + (minutes_after * 60)
    job_id = schedule_callback(user["user_id"], to_phone, when)
    return {"message": "Callback scheduled", "job_id": job_id}
