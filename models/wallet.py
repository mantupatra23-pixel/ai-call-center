from pydantic import BaseModel

class Wallet(BaseModel):
    customer_id: str
    balance: float = 0.0
