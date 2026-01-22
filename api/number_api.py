from fastapi import APIRouter, HTTPException
from db.redis import redis_db
from services.twilio_numbers import buy_number
import json, uuid

router = APIRouter(prefix="/numbers", tags=["Numbers"])

# -------- ADMIN: ADD NUMBER TO POOL --------
@router.post("/admin/buy")
def admin_buy_number(country: str):
    phone = buy_number(country)

    data = {
        "phone_number": phone,
        "country": country,
        "status": "available",
        "customer_id": None
    }

    redis_db.set(f"number:{phone}", json.dumps(data))
    redis_db.sadd("numbers:available", phone)

    return {"message": "Number added to pool", "phone_number": phone}


# -------- CUSTOMER: VIEW AVAILABLE NUMBERS --------
@router.get("/available")
def list_available_numbers(country: str | None = None):
    phones = redis_db.smembers("numbers:available")
    result = []

    for p in phones:
        data = json.loads(redis_db.get(f"number:{p}"))
        if country and data["country"] != country:
            continue
        result.append({"phone_number": p, "country": data["country"]})

    return result


# -------- ADMIN: ASSIGN NUMBER AFTER PAYMENT --------
@router.post("/admin/assign")
def assign_number_to_customer(phone_number: str, customer_id: str):
    key = f"number:{phone_number}"
    raw = redis_db.get(key)
    if not raw:
        raise HTTPException(404, "Number not found")

    num = json.loads(raw)
    if num["status"] != "available":
        raise HTTPException(400, "Number not available")

    num["status"] = "active"
    num["customer_id"] = customer_id

    redis_db.set(key, json.dumps(num))
    redis_db.srem("numbers:available", phone_number)
    redis_db.sadd(f"customer:{customer_id}:numbers", phone_number)

    return {"message": "Number assigned", "phone_number": phone_number}


# -------- CUSTOMER: MY ACTIVE NUMBERS --------
@router.get("/customer/{customer_id}")
def customer_numbers(customer_id: str):
    phones = redis_db.smembers(f"customer:{customer_id}:numbers")
    result = []
    for p in phones:
        data = json.loads(redis_db.get(f"number:{p}"))
        if data["status"] == "active":
            result.append(p)
    return result


# -------- ADMIN: EXPIRE / BYE NUMBER --------
@router.post("/admin/expire")
def expire_number(phone_number: str):
    key = f"number:{phone_number}"
    raw = redis_db.get(key)
    if not raw:
        raise HTTPException(404, "Number not found")

    num = json.loads(raw)
    num["status"] = "expired"

    redis_db.set(key, json.dumps(num))
    redis_db.srem("numbers:available", phone_number)

    if num["customer_id"]:
        redis_db.srem(f"customer:{num['customer_id']}:numbers", phone_number)

    return {"message": "Number expired and hidden"}
