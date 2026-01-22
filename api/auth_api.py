from fastapi import APIRouter, HTTPException
from core.security import hash_password, verify_password, create_access_token
from db.redis import redis_db
import json, uuid

router = APIRouter(prefix="/auth", tags=["Auth"])

# -------- REGISTER (CUSTOMER) --------
@router.post("/register")
def register(email: str, password: str, company_name: str):
    user_id = str(uuid.uuid4())

    if redis_db.get(f"user:{email}"):
        raise HTTPException(400, "User already exists")

    user = {
        "user_id": user_id,
        "email": email,
        "password": hash_password(password),
        "role": "customer",
        "company_name": company_name
    }

    redis_db.set(f"user:{email}", json.dumps(user))

    return {"message": "Registered successfully"}

# -------- LOGIN (ADMIN / CUSTOMER) --------
@router.post("/login")
def login(email: str, password: str):
    raw = redis_db.get(f"user:{email}")
    if not raw:
        raise HTTPException(400, "Invalid credentials")

    user = json.loads(raw)
    if not verify_password(password, user["password"]):
        raise HTTPException(400, "Invalid credentials")

    token = create_access_token({
        "user_id": user["user_id"],
        "email": email,
        "role": user["role"]
    })

    return {"access_token": token, "token_type": "bearer"}
