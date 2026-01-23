import razorpay
import os

client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID"),
        os.getenv("RAZORPAY_KEY_SECRET")
    )
)

def create_order(amount, invoice_id):
    return client.order.create({
        "amount": int(amount * 100),  # rupees → paise
        "currency": "INR",
        "receipt": invoice_id,
        "payment_capture": 1
    })

def verify_signature(payload, signature, secret):
    import hmac, hashlib
    body = payload.encode()
    generated = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return generated == signature
