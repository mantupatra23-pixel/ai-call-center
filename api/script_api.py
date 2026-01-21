import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter()

DATA_FILE = "data/script.json"

class ScriptModel(BaseModel):
    language: str
    intents: dict


@router.post("/upload-script")
def upload_script(script: ScriptModel):
    try:
        os.makedirs("data", exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(script.dict(), f, indent=2)
        return {"status": "script saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-reply/{intent}")
def get_reply(intent: str):
    try:
        with open(DATA_FILE) as f:
            script = json.load(f)

        return {
            "reply": script["intents"].get(
                intent,
                script["intents"].get("fallback", "Sorry, samajh nahi aaya")
            )
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Script not uploaded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
