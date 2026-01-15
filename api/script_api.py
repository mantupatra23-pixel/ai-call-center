import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ScriptModel(BaseModel):
    language: str
    intents: dict

@router.post("/upload-script")
def upload_script(script: ScriptModel):
    try:
        with open("data/script.json", "w") as f:
            json.dump(script.dict(), f, indent=2)
        return {"status": "script saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-reply/{intent}")
def get_reply(intent: str):
    try:
        with open("data/script.json") as f:
            script = json.load(f)
        return {
            "reply": script["intents"].get(
                intent,
                script["intents"]["fallback"]
            )
        }
    except:
        raise HTTPException(status_code=404, detail="script not found")
