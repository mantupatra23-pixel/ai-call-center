from fastapi import APIRouter, Depends
from services.dnc_service import add_dnc, remove_dnc
from core.deps import get_current_user

router = APIRouter(prefix="/dnc", tags=["DNC"])

@router.post("/add")
def add(phone: str, user=Depends(get_current_user)):
    add_dnc(user["user_id"], phone)
    return {"message": "Number added to DNC"}

@router.post("/remove")
def remove(phone: str, user=Depends(get_current_user)):
    remove_dnc(user["user_id"], phone)
    return {"message": "Number removed from DNC"}
