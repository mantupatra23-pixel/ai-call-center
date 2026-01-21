import json
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])

LOG_PATH = "data/call_logs.json"

def load_logs():
    try:
        with open(LOG_PATH) as f:
            return json.load(f)
    except:
        return []

@router.get("/calls")
def all_calls():
    return load_logs()

@router.get("/stats")
def stats():
    logs = load_logs()
    emotions = {}
    languages = {}

    for l in logs:
        emotions[l["emotion"]] = emotions.get(l["emotion"], 0) + 1

    return {
        "total_calls": len(logs),
        "emotion_stats": emotions
    }
