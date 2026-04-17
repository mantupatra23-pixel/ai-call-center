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
    description="High-Speed AI Call Center Backend",
    version="2.0.0"
)

# --- CORS CONFIG ---
# Isse frontend se backend connect hone mein block nahi hoga
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
from api.dashboard_api import router as dashboard_router
from api.wallet_api import router as wallet_router
from api.billing_api import router as billing_router
from api.vapi_whatsapp_api import router as whatsapp_router

# --- ROUTERS MOUNT (SYNCED WITH FRONTEND) ---

# 1. Voice & Call (Frontend hit: /voice/start)
app.include_router(voice_router, prefix="/voice", tags=["Voice"])

# 2. Wallet & Billing (Frontend hit: /wallet/balance/...)
app.include_router(wallet_router, prefix="/wallet", tags=["Wallet"])
app.include_router(billing_router, prefix="/billing", tags=["Billing"])

# 3. Dashboard Stats (Frontend hit: /dashboard/stats)
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

# 4. Call Control & Webhooks
app.include_router(call_router, prefix="/call", tags=["Call"])
app.include_router(vapi_webhook_router, prefix="/vapi", tags=["Vapi Webhook"])
app.include_router(vapi_live_router, prefix="/vapi-live", tags=["Vapi Live"])
app.include_router(vapi_record_router, prefix="/vapi-recording", tags=["Vapi Recording"])
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])

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
