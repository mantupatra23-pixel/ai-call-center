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
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_admin(current_user = Depends(get_current_user)):
    """Dependency to check if current user is an admin."""
    # Agar user ke data mein role 'admin' nahi hai, toh access deny kar do
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user
