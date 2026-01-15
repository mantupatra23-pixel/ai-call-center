from fastapi import FastAPI

# Routers import
from api.script_api import router as script_router
from api.voice_api import router as voice_router

app = FastAPI(
    title="AI Call Center",
    description="Web-based AI Call Center Backend",
    version="1.0.0"
)

# Include routers
app.include_router(script_router)
app.include_router(voice_router)

@app.get("/")
def home():
    return {"status": "AI Call Center Live"}
