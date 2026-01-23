# services/invoice_service.py

import io
import json
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from db.redis import redis_db

def generate_invoice_pdf(customer_id: str, month: str):
    """
    month format: YYYY-MM
    """
    logs = redis_db.lrange("billing:logs", 0, -1)
    items = []
    total = 0

    for log in logs:
        data = json.loads(log)
        if data["customer_id"] == customer_id and data.get("month") == month:
            items.append(data)
            total += data["cost"]

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "INVOICE")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Customer ID: {customer_id}")
    y -= 15
    pdf.drawString(40, y, f"Billing Month: {month}")
    y -= 25

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, y, "Call SID")
    pdf.drawString(200, y, "Minutes")
    pdf.drawString(300, y, "Rate")
    pdf.drawString(380, y, "Cost")
    y -= 15

    pdf.setFont("Helvetica", 10)
    for item in items:
        pdf.drawString(40, y, item.get("call_sid", "-")[:18])
        pdf.drawString(200, y, str(item["minutes"]))
        pdf.drawString(300, str(item["rate"]))
        pdf.drawString(380, str(item["cost"]))
        y -= 14
        if y < 60:
            pdf.showPage()
            y = height - 40

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(300, y, "TOTAL:")
    pdf.drawString(380, y, str(total))

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer, total
