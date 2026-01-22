from pydantic import BaseModel

class Number(BaseModel):
    phone_number: str
    country: str
    status: str = "available"  # available / active / expired / released
    customer_id: str | None = None
