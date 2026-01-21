import json, os
from fastapi import APIRouter

router = APIRouter()

DATA_PATH = "data/call_logs.json"

@router.get("/dashboard/stats")
def dashboard_stats():
    if not os.path.exists(DATA_PATH):
        return {}

    with open(DATA_PATH) as f:
        data = json.load(f)

    emotions = {}
    for c in data:
        emotions[c["emotion"]] = emotions.get(c["emotion"], 0) + 1

    return {
        "total_calls": len(data),
        "emotion_breakdown": emotions,
        "recent_calls": data[-20:]
    }
