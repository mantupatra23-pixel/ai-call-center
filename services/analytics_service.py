from db.redis import redis_db
import json, time

def _today():
    return time.strftime('%Y-%m-%d')

def _month():
    return time.strftime('%Y-%m')

# -------- CUSTOMER METRICS --------
def customer_daily_metrics(customer_id: str):
    sids = redis_db.smembers(f"customer:{customer_id}:calls")
    calls = minutes = cost = 0

    for sid in sids:
        raw = redis_db.get(f"call:{sid}")
        if not raw: 
            continue
        c = json.loads(raw)
        if c.get("status") == "completed" and c.get("completed_at", "").startswith(_today()):
            calls += 1
            minutes += max(1, c.get("duration_sec", 0)//60)
            cost += c.get("cost", 0.0)

    return {"calls": calls, "minutes": minutes, "cost": round(cost, 2)}

def customer_monthly_metrics(customer_id: str):
    sids = redis_db.smembers(f"customer:{customer_id}:calls")
    calls = minutes = cost = 0

    for sid in sids:
        raw = redis_db.get(f"call:{sid}")
        if not raw: 
            continue
        c = json.loads(raw)
        if c.get("status") == "completed" and c.get("completed_at", "").startswith(_month()):
            calls += 1
            minutes += max(1, c.get("duration_sec", 0)//60)
            cost += c.get("cost", 0.0)

    return {"calls": calls, "minutes": minutes, "cost": round(cost, 2)}

# -------- ADMIN METRICS --------
def admin_overview():
    total_calls = total_cost = 0
    for key in redis_db.scan_iter("call:*"):
        raw = redis_db.get(key)
        if not raw:
            continue
        c = json.loads(raw)
        if c.get("status") == "completed":
            total_calls += 1
            total_cost += c.get("cost", 0.0)

    return {
        "total_calls": total_calls,
        "total_revenue": round(total_cost, 2)
    }
