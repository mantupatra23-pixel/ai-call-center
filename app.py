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

# --- CORS CONFIG ---
# Production mein security ke liye ye zaroori hai
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URL set karne par aur secure ho jayega
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC FILES (For Logs/Recordings) ---
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ROUTERS IMPORT ---
# Core logic
from api.auth_api import router as auth_router
from api.voice_api import router as voice_router
from api.call_api import router as call_router

# Management
from api.customer_api import router as customer_router
from api.dashboard_api import router as dashboard_router
from api.wallet_api import router as wallet_router
from api.billing_api import router as billing_router
from api.admin_dashboard_api import router as admin_router

# Webhooks (Vapi Logic)
from api.vapi_webhook_api import router as vapi_webhook_router
from api.vapi_live_api import router as vapi_live_router
from api.vapi_recording_api import router as vapi_record_router

# Advanced Systems
from api.dnc_api import router as dnc_router
from api.working_hours_api import router as hours_router
from api.revenue_guard_api import router as revenue_router

# --- ROUTERS MOUNT ---

# 1. Voice & Call (Primary)
app.include_router(voice_router, prefix="/voice", tags=["Voice Engine"])
app.include_router(call_router, prefix="/call", tags=["Call Control"])

# 2. Vapi Webhooks (Bohot Zaroori)
app.include_router(vapi_webhook_router, prefix="/vapi", tags=["Vapi Webhook"])
app.include_router(vapi_live_router, prefix="/vapi-live", tags=["Vapi Live"])
app.include_router(vapi_record_router, prefix="/vapi-recording", tags=["Vapi Recording"])

# 3. Business Logic & Management
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(customer_router, prefix="/customer", tags=["Customer"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(wallet_router, prefix="/wallet", tags=["Wallet"])
app.include_router(billing_router, prefix="/billing", tags=["Billing"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

# 4. Safety Systems
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
    print(f"REDIS_STATUS = Connected to {os.getenv('REDIS_URL', 'Local')}")
    print(f"VOICE_ENGINE = Vapi AI Integrated")
    print(f"PUBLIC_URL = {os.getenv('PUBLIC_BASE_URL', 'Not Set')}")
