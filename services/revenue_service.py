# services/revenue_service.py

import json
import datetime
from db.redis import redis_db

def _today_range():
    now = datetime.datetime.utcnow()
    start = datetime.datetime(now.year, now.month, now.day)
    end = start + datetime.timedelta(days=1)
    return int(start.timestamp()), int(end.timestamp())

def _month_range():
    now = datetime.datetime.utcnow()
    start = datetime.datetime(now.year, now.month, 1)
    if now.month == 12:
        end = datetime.datetime(now.year + 1, 1, 1)
    else:
        end = datetime.datetime(now.year, now.month + 1, 1)
    return int(start.timestamp()), int(end.timestamp())

def revenue_summary():
    wallet = float(redis_db.get("admin:revenue:wallet") or 0)
    sub = float(redis_db.get("admin:revenue:subscription") or 0)
    return {
        "wallet_revenue": wallet,
        "subscription_revenue": sub,
        "total_revenue": wallet + sub
    }

def revenue_today():
    start, end = _today_range()
    logs = redis_db.lrange("billing:logs", 0, -1)
    total = 0.0
    for l in logs:
        d = json.loads(l)
        ts = int(d.get("ended_at", d.get("timestamp", 0)))
        if start <= ts < end:
            total += float(d.get("cost", 0))
    return total

def revenue_month():
    start, end = _month_range()
    logs = redis_db.lrange("billing:logs", 0, -1)
    total = 0.0
    for l in logs:
        d = json.loads(l)
        ts = int(d.get("ended_at", d.get("timestamp", 0)))
        if start <= ts < end:
            total += float(d.get("cost", 0))
    return total

def customer_wise_revenue():
    logs = redis_db.lrange("billing:logs", 0, -1)
    out = {}
    for l in logs:
        d = json.loads(l)
        cid = d.get("customer_id")
        out[cid] = out.get(cid, 0) + float(d.get("cost", 0))
    return out

def plan_sales():
    return redis_db.hgetall("admin:subscription:sales") or {}
