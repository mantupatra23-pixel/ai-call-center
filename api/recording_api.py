# api/recording_api.py

import json
from fastapi import APIRouter, Depends
from core.auth_guard import get_current_user
from db.redis import redis_db

router = APIRouter(prefix="/recordings", tags=["Recordings"])

@router.get("/my")
def my_recordings(user=Depends(get_current_user)):
    logs = redis_db.lrange(
        f"customer:{user['id']}:recordings", 0, -1
    )
    return [json.loads(l) for l in logs]
