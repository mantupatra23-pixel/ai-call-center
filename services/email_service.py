# services/email_service.py

import os
import smtplib
from email.message import EmailMessage

def send_invoice_email(to_email: str, pdf_bytes: bytes, month: str):
    msg = EmailMessage()
    msg["Subject"] = f"Your Invoice - {month}"
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = to_email

    msg.set_content(
        f"Hello,\n\nPlease find attached your invoice for {month}.\n\nThank you."
    )

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"invoice-{month}.pdf"
    )

    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        server.send_message(msg)
