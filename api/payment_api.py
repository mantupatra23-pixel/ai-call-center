import json
from fastapi import APIRouter, Request, HTTPException
from db.redis import redis_db
from services.razorpay_service import create_order, verify_signature
import os

router = APIRouter(prefix="/payment", tags=["Payment"])

# -------------------------------------------------
# CREATE PAYMENT ORDER
# -------------------------------------------------
@router.post("/create-order")
def create_payment_order(invoice_id: str):
    raw = redis_db.get(f"invoice:{invoice_id}")
    if not raw:
        raise HTTPException(404, "Invoice not found")

    invoice = json.loads(raw)

    if invoice["status"] != "pending":
        raise HTTPException(400, "Invoice already paid")

    order = create_order(invoice["price_total"], invoice_id)

    redis_db.set(
        f"razorpay:order:{order['id']}",
        json.dumps({
            "invoice_id": invoice_id,
            "amount": invoice["price_total"]
        })
    )

    return {
        "order_id": order["id"],
        "amount": invoice["price_total"],
        "currency": "INR",
        "key": os.getenv("RAZORPAY_KEY_ID")
    }

# -------------------------------------------------
# RAZORPAY WEBHOOK
# -------------------------------------------------
@router.post("/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not verify_signature(
        body.decode(),
        signature,
        os.getenv("RAZORPAY_WEBHOOK_SECRET")
    ):
        raise HTTPException(400, "Invalid signature")

    payload = json.loads(body)
    event = payload["event"]

    if event == "payment.captured":
        order_id = payload["payload"]["payment"]["entity"]["order_id"]

        raw = redis_db.get(f"razorpay:order:{order_id}")
        if not raw:
            return {"status": "ignored"}

        data = json.loads(raw)
        invoice_id = data["invoice_id"]

        invoice = json.loads(redis_db.get(f"invoice:{invoice_id}"))
        invoice["status"] = "paid"

        redis_db.set(f"invoice:{invoice_id}", json.dumps(invoice))

    return {"status": "ok"}
