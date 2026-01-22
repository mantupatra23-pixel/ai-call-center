from pydantic import BaseModel, EmailStr

class CustomerCreate(BaseModel):
    company_name: str
    email: EmailStr
    company_type: str   # finance / ecommerce / support
    country: str        # IN / UAE / US


class Customer(CustomerCreate):
    customer_id: str
    status: str = "pending"   # pending / approved / blocked
