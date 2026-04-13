import os
from groq import Groq

# Memory (same use karenge)
from services.ai_memory_service import (
    get_summary,
    add_customer_memory,
)

# =========================
# GROQ CLIENT
# =========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY missing")

client = Groq(api_key=GROQ_API_KEY)

# =========================
# AI AGENT REPLY
# =========================
def ai_reply(
    user_text: str,
    company_profile: dict,
    lang: str = "hi",
    customer_id: str | None = None
):
    """
    AI voice agent reply with:
    - Company context
    - Customer memory
    - Short polite responses
    """

    # =========================
    # SYSTEM PROMPT
    # =========================
    system_prompt = f"""
You are an AI call center voice agent.

Company Profile:
Company Name: {company_profile.get("company_name")}
Business Type: {company_profile.get("business_type")}
Services: {", ".join(company_profile.get("services", []))}
Working Hours: {company_profile.get("working_hours")}
Tone: {company_profile.get("tone")}

Rules:
- Be polite and natural
- Keep replies short
- If confused, ask a clarification
- If customer says bye, end politely
- Speak only in language: {lang}
"""

    # =========================
    # CUSTOMER MEMORY
    # =========================
    if customer_id:
        summary = get_summary(customer_id)
        if summary:
            system_prompt += f"\nCustomer Past Context:\n{summary}\n"

    # =========================
    # GROQ CALL
    # =========================
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.4
        )

        reply = response.choices[0].message.content.strip()

    except Exception as e:
        print("Groq Error:", e)
        reply = "Maaf kijiye, system me thodi problem hai."

    # =========================
    # SAVE MEMORY
    # =========================
    if customer_id:
        add_customer_memory(
            customer_id,
            {
                "user": user_text,
                "ai": reply
            }
        )

    return reply
