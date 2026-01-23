from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from core.security import decode_token
from db.redis import redis_db
import json

security = HTTPBearer()

def get_current_user(token=Depends(security)):
    try:
        payload = decode_token(token.credentials)
        user_id = payload["sub"]
        user_raw = redis_db.get(f"user:{user_id}")

        if not user_raw:
            raise Exception()

        return json.loads(user_raw)

    except:
        raise HTTPException(401, "Invalid or expired token")
