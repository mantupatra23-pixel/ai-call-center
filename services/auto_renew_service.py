import time, json
from db.redis import redis_db
from services.wallet_service import deduct_balance

def try_auto_renew(customer_id: str):
    sub_key = f"customer:{customer_id}:subscription"
    raw = redis_db.get(sub_key)
    if not raw:
        return False

    sub = json.loads(raw)

    if not sub.get("auto_renew"):
        return False

    now = int(time.time())
    expired = sub["expires_at"] <= now
    no_minutes = sub["minutes_left"] <= 0

    if not expired and not no_minutes:
        return False

    plans = json.loads(redis_db.get("sub:plans"))
    plan = plans.get(sub["plan_id"])
    if not plan:
        return False

    # 🔥 Wallet charge
    balance = deduct_balance(customer_id, plan["price"])
    if balance < 0:
        return False

    # 🔁 Renew
    sub["minutes_left"] = plan["minutes"]
    sub["expires_at"] = now + plan["validity_days"] * 86400

    redis_db.set(sub_key, json.dumps(sub))
    return True
