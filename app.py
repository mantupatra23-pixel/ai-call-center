import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --- ENV LOAD ---
load_dotenv()

# --- FASTAPI CORE ---
app = FastAPI(
    title="Vaani AI - Voice Engine",
    description="High-Speed AI Call Center Backend (Vapi + Groq)",
    version="2.0.0"
)

# --- CORS CONFIG (SaaS Dashboard ke liye zaroori) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production mein yahan apna frontend URL dalo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC FILES (Recordings & Audio storage) ---
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ROUTERS IMPORT ---

# 1. Core Call & Voice Logic
from api.voice_api import router as voice_router
from api.call_api import router as call_router

# 2. Vapi Webhooks (Twilio Bypass)
from api.vapi_webhook_api import router as vapi_webhook_router
from api.vapi_live_api import router as vapi_live_router
from api.vapi_recording_api import router as vapi_record_router

# 3. User & Admin Management
from api.auth_api import router as auth_router
from api.customer_api import router as customer_router
from api.dashboard_api import router as dashboard_router
from api.wallet_api import router as wallet_router
from api.billing_api import router as billing_router
from api.admin_dashboard_api import router as admin_router

# 4. Advanced Logic & Safety
from api.vapi_whatsapp_api import router as whatsapp_router
from api.dnc_api import router as dnc_router
from api.working_hours_api import router as hours_router
from api.revenue_guard_api import router as revenue_router

# --- ROUTERS MOUNT ---

# Call Engine Routes
app.include_router(voice_router, prefix="/voice", tags=["Voice Engine"])
app.include_router(call_router, prefix="/call", tags=["Call Control"])

# Vapi Webhook Routes
app.include_router(vapi_webhook_router, prefix="/vapi", tags=["Vapi Webhook"])
app.include_router(vapi_live_router, prefix="/vapi-live", tags=["Vapi Live"])
app.include_router(vapi_record_router, prefix="/vapi-recording", tags=["Vapi Recording"])

# Management Routes
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(customer_router, prefix="/customer", tags=["Customer"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(wallet_router, prefix="/wallet", tags=["Wallet"])
app.include_router(billing_router, prefix="/billing", tags=["Billing"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

# Safety & Social Routes
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])
app.include_router(dnc_router, prefix="/dnc", tags=["DNC"])
app.include_router(hours_router, prefix="/hours", tags=["Working Hours"])
app.include_router(revenue_router, prefix="/revenue", tags=["Revenue Guard"])

# --- HEALTH CHECK ---
@app.get("/", tags=["Health"])
def home():
    return {
        "status": "Vaani AI Backend Live",
        "engine": "Vapi + Groq Llama-3",
        "version": "2.0.0",
        "author": "Visora AI Labs"
    }

# --- STARTUP EVENT ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Vaani AI - High Speed Voice Engine Started")
    print(f"REDIS_URL = {os.getenv('REDIS_URL', 'Local Connection')}")
    print(f"VOICE_ENGINE = Vapi AI Integration Active")
