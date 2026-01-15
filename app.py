from fastapi import FastAPI
from api.script_api import router

app = FastAPI()
app.include_router(router)

@app.get("/")
def home():
    return {"status": "AI Call Center Live"}
