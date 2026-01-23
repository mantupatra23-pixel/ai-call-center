# services/sales_service.py

def detect_sales_intent(text: str):
    text = text.lower()

    if any(k in text for k in ["price", "cost", "rate", "kitna", "charges"]):
        return "pricing"

    if any(k in text for k in ["demo", "trial", "test"]):
        return "demo"

    if any(k in text for k in ["buy", "purchase", "order", "subscribe"]):
        return "buy"

    if any(k in text for k in ["book", "appointment", "meeting"]):
        return "booking"

    return "general"


def upsell_reply(intent: str):
    if intent == "pricing":
        return "Humare plans flexible hain. Aaj demo free hai. Demo book karein?"
    if intent == "demo":
        return "Demo bilkul free hai. Main abhi booking kar deta hoon."
    if intent == "buy":
        return "Great choice! Aaj limited-time discount available hai."
    if intent == "booking":
        return "Perfect! Main aapki booking note kar raha hoon."
    return None
