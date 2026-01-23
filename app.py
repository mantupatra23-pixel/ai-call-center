# app.py
# =====================================================
# ENV LOAD (VERY IMPORTANT)
# =====================================================
from dotenv import load_dotenv
load_dotenv()

import os

# =====================================================
# FASTAPI CORE
# =====================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# =====================================================
# ROUTERS IMPORT
# =====================================================
from api.auth_api import router as auth_router
from api.voice_api import router as voice_router
from api.script_api import router as script_router
from api.customer_api import router as customer_router
from api.admin_api import router as admin_router
from api.dashboard_api import router as dashboard_router
from api.call_api import router as call_router
from api.number_api import router as number_router
from api.wallet_api import router as wallet_router
from api.invoice_api import router as invoice_router
from api.safety_api import router as safety_router
from api.billing_api import router as billing_router
from api.payment_api import router as payment_router
from api.subscription_api import router as subscription_router
from api.admin_dashboard_api import router as admin_dashboard_router

# Webhooks / Advanced
from api.twilio_webhook_api import router as twilio_router
from api.recording_webhook_api import router as recording_router
from api.analytics_api import router as analytics_router
from api.webhook_retry_api import router as retry_router
from api.dnc_api import router as dnc_router
from api.working_hours_api import router as hours_router
from api.revenue_guard_api import router as revenue_router

# =====================================================
# APP INIT
# =====================================================
app = FastAPI(
    title="AI Call Center SaaS",
    description="Web-based AI Call Center Backend",
    version="1.0.0"
)

# =====================================================
# CORS (OPEN – dashboard + mobile safe)
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# STATIC FILES (TTS AUDIO)
# Example: /static/voice/xxxx.mp3
# =====================================================
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# =====================================================
# ROUTERS MOUNT
# =====================================================
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(voice_router, prefix="/voice", tags=["Voice"])
app.include_router(script_router, prefix="/script", tags=["Script"])
app.include_router(customer_router, prefix="/customer", tags=["Customer"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(call_router, prefix="/call", tags=["Call"])
app.include_router(number_router, prefix="/number", tags=["Number"])
app.include_router(wallet_router, prefix="/wallet", tags=["Wallet"])
app.include_router(invoice_router, prefix="/invoice", tags=["Invoice"])
app.include_router(safety_router, prefix="/safety", tags=["Safety"])
app.include_router(billing_router, tags=["Billing"])
app.include_router(payment_router, tags=["Payment"])
app.include_router(subscription_router, tags=["Subscription"])
app.include_router(admin_dashboard_router, tags=["Admin Dashboard"])

# =====================================================
# WEBHOOKS
# =====================================================
app.include_router(twilio_router, prefix="/twilio", tags=["Twilio"])
app.include_router(recording_router, prefix="/recording", tags=["Recording"])

# =====================================================
# ADVANCED SYSTEMS
# =====================================================
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
app.include_router(retry_router, prefix="/retry", tags=["Retry"])
app.include_router(dnc_router, prefix="/dnc", tags=["DNC"])
app.include_router(hours_router, prefix="/hours", tags=["Working Hours"])
app.include_router(revenue_router, prefix="/revenue", tags=["Revenue"])

# =====================================================
# HEALTH CHECK
# =====================================================
@app.get("/", tags=["Health"])
def home():
    return {
        "status": "AI Call Center Backend Live",
        "version": "1.0.0"
    }

# =====================================================
# STARTUP EVENT
# =====================================================
@app.on_event("startup")
async def startup_event():
    print("🚀 AI Call Center Backend Started")
    print("PUBLIC_BASE_URL =", os.getenv("PUBLIC_BASE_URL"))
    print("REDIS_URL =", os.getenv("REDIS_URL"))
