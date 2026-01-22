from fastapi import APIRouter
from models.customer import CustomerCreate
from db.redis import redis_db
import uuid, json

router = APIRouter(prefix="/customer", tags=["Customer"])

@router.post("/register")
def register_customer(data: CustomerCreate):
    customer_id = str(uuid.uuid4())

    customer_data = {
        "customer_id": customer_id,
        "company_name": data.company_name,
        "email": data.email,
        "company_type": data.company_type,
        "country": data.country,
        "status": "pending"
    }

    redis_db.set(
        f"customer:{customer_id}",
        json.dumps(customer_data)
    )

    redis_db.sadd("customers:pending", customer_id)

    return {
        "message": "Registration successful",
        "customer_id": customer_id,
        "status": "pending"
    }


@router.get("/status/{customer_id}")
def check_status(customer_id: str):
    data = redis_db.get(f"customer:{customer_id}")
    if not data:
        return {"error": "Customer not found"}

    customer = json.loads(data)
    return {
        "customer_id": customer_id,
        "status": customer["status"]
    }
