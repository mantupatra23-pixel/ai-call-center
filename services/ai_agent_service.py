# services/ai_agent_service.py

import os
from openai import OpenAI

from services.ai_memory_service import (
    get_summary,
    add_customer_memory,
)

# =========================
# OPENAI CLIENT
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing")

client = OpenAI(api_key=OPENAI_API_KEY)

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
    # OPENAI CALL
    # =========================
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_text}
        ],
        temperature=0.4
    )

    reply = response.choices[0].message.content.strip()

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
