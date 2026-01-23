# api/invoice_api.py

import uuid
import json
import time
import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from db.redis import redis_db
from core.auth_guard import get_current_user
from models.invoice import InvoiceCreate
from services.invoice_service import generate_invoice_pdf
from services.email_service import send_invoice_email

router = APIRouter(prefix="/invoice", tags=["Invoice"])

# =========================================================
# ADMIN: CREATE INVOICE (PRICE ADMIN DECIDES)
# =========================================================
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

# =========================================================
# CUSTOMER: LIST MY INVOICES
# =========================================================
@router.get("/my")
def my_invoices(user=Depends(get_current_user)):
    ids = redis_db.smembers(f"customer:{user['id']}:invoices")
    invoices = []

    for iid in ids:
        raw = redis_db.get(f"invoice:{iid}")
        if raw:
            invoices.append(json.loads(raw))

    return invoices

# =========================================================
# CUSTOMER: PAY INVOICE (MANUAL / GATEWAY HOOK READY)
# =========================================================
@router.post("/pay")
def pay_invoice(invoice_id: str, user=Depends(get_current_user)):
    raw = redis_db.get(f"invoice:{invoice_id}")
    if not raw:
        raise HTTPException(404, "Invoice not found")

    invoice = json.loads(raw)

    if invoice["customer_id"] != user["id"]:
        raise HTTPException(403, "Not your invoice")

    if invoice["status"] != "pending":
        raise HTTPException(400, "Invoice already processed")

    # ---- PAYMENT SUCCESS (SIMULATED / WEBHOOK ENTRY POINT)
    invoice["status"] = "paid"
    invoice["paid_at"] = int(time.time())
    redis_db.set(f"invoice:{invoice_id}", json.dumps(invoice))

    # ---- ACTIVATE NUMBERS AFTER PAYMENT
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

# =========================================================
# ADMIN: EXPIRE INVOICE (OPTIONAL)
# =========================================================
@router.post("/admin/expire")
def expire_invoice(invoice_id: str):
    raw = redis_db.get(f"invoice:{invoice_id}")
    if not raw:
        raise HTTPException(404, "Invoice not found")

    invoice = json.loads(raw)
    invoice["status"] = "expired"

    redis_db.set(f"invoice:{invoice_id}", json.dumps(invoice))
    return {"message": "Invoice expired"}

# =========================================================
# CUSTOMER: DOWNLOAD MONTHLY AUTO INVOICE (PDF)
# =========================================================
@router.get("/my/pdf")
def my_invoice_pdf(user=Depends(get_current_user)):
    month = datetime.date.today().strftime("%Y-%m")
    pdf_buffer, total = generate_invoice_pdf(user["id"], month)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice-{month}.pdf"
        }
    )

# =========================================================
# CUSTOMER: EMAIL MONTHLY AUTO INVOICE
# =========================================================
@router.post("/my/email")
def email_my_invoice(user=Depends(get_current_user)):
    month = datetime.date.today().strftime("%Y-%m")
    pdf_buffer, total = generate_invoice_pdf(user["id"], month)

    send_invoice_email(
        to_email=user["email"],
        pdf_bytes=pdf_buffer.getvalue(),
        month=month
    )

    return {
        "status": "sent",
        "month": month,
        "total": total
    }
