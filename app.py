from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# =========================
# Routers
# =========================
from api.voice_api import router as voice_router
from api.script_api import router as script_router
from api.admin_api import router as admin_router
from api.dashboard_api import router as dashboard_router

# =========================
# App Init
# =========================
app = FastAPI(
    title="AI Call Center",
    description="Web-based AI Call Center Backend",
    version="1.0.0"
)

app.include_router(dashboard_router)

# =========================
# 🔥 CORS (Allow All)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 🔥 STATIC FILES (TTS Audio)
# =========================
# Folder: static/
# Use for Google TTS / ElevenLabs generated audio
app.mount("/static", StaticFiles(directory="static"), name="static")

# =========================
# 🔥 ROUTERS
# =========================
app.include_router(
    voice_router,
    prefix="/voice",
    tags=["Voice Call API"]
)

app.include_router(
    script_router,
    prefix="/script",
    tags=["AI Script API"]
)

app.include_router(
    admin_router,
    prefix="/admin",
    tags=["Admin API"]
)

# =========================
# 🔥 HEALTH CHECK
# =========================
@app.get("/", tags=["Health"])
def home():
    return {
        "status": "AI Call Center Live",
        "version": "1.0.0"
    }

# =========================
# 🔥 STARTUP LOG
# =========================
@app.on_event("startup")
async def startup_event():
    print("🚀 AI Call Center Backend Started")
