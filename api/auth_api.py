from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from core.security import hash_password, verify_password, create_access_token
from db.redis import redis_db
import uuid, json, random, smtplib, os
from email.mime.text import MIMEText

router = APIRouter(prefix="/auth", tags=["Auth"])

# =====================
# MODELS
# =====================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class OTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


# =====================
# EMAIL SENDER
# =====================
def send_email_otp(to_email: str, otp: str):
    msg = MIMEText(f"Your OTP is: {otp}\nValid for 5 minutes.")
    msg["Subject"] = "Your Login OTP"
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = to_email

    server = smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT")))
    server.starttls()
    server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
    server.send_message(msg)
    server.quit()


# =====================
# REGISTER
# =====================
@router.post("/register")
def register(data: RegisterRequest):
    email = data.email.lower()

    if redis_db.get(f"user:email:{email}"):
        raise HTTPException(400, "Email already registered")

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "password": hash_password(data.password),
        "company_name": data.company_name,
        "role": "customer",
        "wallet": 0,
        "is_verified": False
    }

    redis_db.set(f"user:{user_id}", json.dumps(user))
    redis_db.set(f"user:email:{email}", user_id)

    return {"status": "registered", "user_id": user_id}


# =====================
# SEND OTP
# =====================
@router.post("/send-otp")
def send_otp(data: OTPRequest):
    email = data.email.lower()
    user_id = redis_db.get(f"user:email:{email}")

    if not user_id:
        raise HTTPException(404, "User not found")

    otp = str(random.randint(100000, 999999))
    redis_db.setex(f"otp:{email}", 300, otp)

    send_email_otp(email, otp)

    return {"status": "otp_sent"}


# =====================
# VERIFY OTP
# =====================
@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest):
    email = data.email.lower()
    saved_otp = redis_db.get(f"otp:{email}")

    if not saved_otp or saved_otp != data.otp:
        raise HTTPException(400, "Invalid or expired OTP")

    user_id = redis_db.get(f"user:email:{email}")
    user = json.loads(redis_db.get(f"user:{user_id}"))

    user["is_verified"] = True
    redis_db.set(f"user:{user_id}", json.dumps(user))
    redis_db.delete(f"otp:{email}")

    return {"status": "verified"}


# =====================
# LOGIN
# =====================
@router.post("/login")
def login(data: LoginRequest):
    email = data.email.lower()
    user_id = redis_db.get(f"user:email:{email}")

    if not user_id:
        raise HTTPException(401, "Invalid credentials")

    user = json.loads(redis_db.get(f"user:{user_id}"))

    if not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")

    if not user["is_verified"]:
        raise HTTPException(403, "Email not verified")

    token = create_access_token({
        "sub": user["id"],
        "role": user["role"]
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
