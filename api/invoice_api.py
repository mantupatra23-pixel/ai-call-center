from fastapi import APIRouter, HTTPException
from db.redis import redis_db
from models.invoice import InvoiceCreate
import uuid, json, time

router = APIRouter(prefix="/invoice", tags=["Invoice"])

# -------- ADMIN: CREATE INVOICE (PRICE ADMIN DECIDES) --------
@router.post("/admin/create")
def create_invoice(data: InvoiceCreate):
    invoice_id = str(uuid.uuid4())

    invoice = {
        "invoice_id": invoice_id,
        "customer_id": data.customer_id,
        "numbers": data.numbers,
        "price_total": data.price_total,
        "status": "pending",
        "validity_days": data.validity_days,
        "note": data.note,
        "created_at": int(time.time())
    }

    redis_db.set(f"invoice:{invoice_id}", json.dumps(invoice))
    redis_db.sadd(f"customer:{data.customer_id}:invoices", invoice_id)

    return {
        "message": "Invoice created",
        "invoice_id": invoice_id,
        "status": "pending"
    }


# -------- CUSTOMER: VIEW MY INVOICES --------
@router.get("/customer/{customer_id}")
def customer_invoices(customer_id: str):
    ids = redis_db.smembers(f"customer:{customer_id}:invoices")
    invoices = []

    for iid in ids:
        raw = redis_db.get(f"invoice:{iid}")
        if raw:
            invoices.append(json.loads(raw))

    return invoices


# -------- CUSTOMER: PAY INVOICE (MANUAL / GATEWAY HOOK) --------
@router.post("/pay")
def pay_invoice(invoice_id: str):
    raw = redis_db.get(f"invoice:{invoice_id}")
    if not raw:
        raise HTTPException(404, "Invoice not found")

    invoice = json.loads(raw)
    if invoice["status"] != "pending":
        raise HTTPException(400, "Invoice already processed")

    # ---- PAYMENT SUCCESS SIMULATION / WEBHOOK ENTRY POINT ----
    invoice["status"] = "paid"
    redis_db.set(f"invoice:{invoice_id}", json.dumps(invoice))

    # ---- ACTIVATE NUMBERS AFTER PAYMENT ----
    for phone in invoice["numbers"]:
        num_raw = redis_db.get(f"number:{phone}")
        if not num_raw:
            continue

        num = json.loads(num_raw)
        num["status"] = "active"
        num["customer_id"] = invoice["customer_id"]

        redis_db.set(f"number:{phone}", json.dumps(num))
        redis_db.sadd(f"customer:{invoice['customer_id']}:numbers", phone)
        redis_db.srem("numbers:available", phone)

    return {
        "message": "Payment successful, numbers activated",
        "invoice_id": invoice_id
    }


# -------- ADMIN: EXPIRE INVOICE (OPTIONAL) --------
@router.post("/admin/expire")
def expire_invoice(invoice_id: str):
    raw = redis_db.get(f"invoice:{invoice_id}")
    if not raw:
        raise HTTPException(404, "Invoice not found")

    invoice = json.loads(raw)
    invoice["status"] = "expired"
    redis_db.set(f"invoice:{invoice_id}", json.dumps(invoice))

    return {"message": "Invoice expired"}
