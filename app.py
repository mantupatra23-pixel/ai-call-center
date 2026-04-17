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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC FILES ---
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ROUTERS IMPORT ---
from api.voice_api import router as voice_router
from api.call_api import router as call_router
from api.vapi_webhook_api import router as vapi_webhook_router
from api.vapi_live_api import router as vapi_live_router
from api.vapi_recording_api import router as vapi_record_router
from api.auth_api import router as auth_router
from api.customer_api import router as customer_router
from api.dashboard_api import router as dashboard_router
from api.wallet_api import router as wallet_router
from api.billing_api import router as billing_router
from api.admin_dashboard_api import router as admin_router
from api.vapi_whatsapp_api import router as whatsapp_router
from api.dnc_api import router as dnc_router
from api.working_hours_api import router as hours_router
from api.revenue_guard_api import router as revenue_router

# --- ROUTERS MOUNT (CRITICAL FIX FOR 404) ---
# Dhyan dein: Prefix hata diye hain taaki api files ke internal paths kaam karein
app.include_router(voice_router)         # Frontend hits: /voice/start
app.include_router(call_router)          # Frontend hits: /call/end
app.include_router(vapi_webhook_router)  # Vapi hits: /vapi/webhook
app.include_router(vapi_live_router)     # Vapi hits: /vapi-live/balance-check
app.include_router(vapi_record_router)   # Vapi hits: /vapi-recording/callback

# Management & Safety
app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(dashboard_router)     # Frontend hits: /dashboard/stats
app.include_router(wallet_router)        # Frontend hits: /wallet/balance/{id}
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(whatsapp_router)
app.include_router(dnc_router)
app.include_router(hours_router)
app.include_router(revenue_router)

# --- HEALTH CHECK ---
@app.get("/", tags=["Health"])
def home():
    return {
        "status": "Vaani AI Backend Live",
        "engine": "Vapi + Groq Llama-3",
        "version": "2.0.0"
    }

# --- STARTUP EVENT ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Vaani AI - High Speed Voice Engine Started")
    print(f"VOICE_ENGINE = Vapi AI Integration Active")
