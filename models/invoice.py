from pydantic import BaseModel
from typing import List

class InvoiceCreate(BaseModel):
    customer_id: str
    numbers: List[str]          # phone numbers
    price_total: float          # admin-decided price
    validity_days: int = 30     # admin control
    note: str | None = None


class Invoice(BaseModel):
    invoice_id: str
    customer_id: str
    numbers: List[str]
    price_total: float
    status: str                 # pending / paid / expired
    validity_days: int
    note: str | None = None
