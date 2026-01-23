# services/subscription_service.py

import time
import json
from db.redis import redis_db

# =====================================================
# ACTIVATE SUBSCRIPTION PLAN (ADMIN CONTROLLED PRICE)
# =====================================================
def activate_plan(customer_id: str, plan_id: str, auto_renew: bool = True):
    """
    Activate subscription plan for customer
    - Admin defines plans dynamically
    - Minutes + expiry stored
    - Auto-renew supported
    """

    raw = redis_db.get("sub:plans")
    if not raw:
        return False

    plans = json.loads(raw)
    plan = plans.get(plan_id)
    if not plan:
        return False

    price = float(plan.get("price", 0))
    minutes = int(plan.get("minutes", 0))
    validity_days = int(plan.get("validity_days", 0))

    now = int(time.time())

    # ---------- ADMIN REVENUE TRACKING ----------
    redis_db.incrbyfloat(
        "admin:revenue:subscription",
        price
    )

    redis_db.hincrby(
        "admin:subscription:sales",
        plan_id,
        1
    )

    # ---------- SUBSCRIPTION OBJECT ----------
    subscription = {
        "plan_id": plan_id,
        "minutes_left": minutes,
        "price": price,
        "activated_at": now,
        "expires_at": now + validity_days * 86400,
        "auto_renew": auto_renew
    }

    redis_db.set(
        f"customer:{customer_id}:subscription",
        json.dumps(subscription)
    )

    return True


# =====================================================
# GET ACTIVE SUBSCRIPTION
# =====================================================
def get_subscription(customer_id: str):
    raw = redis_db.get(f"customer:{customer_id}:subscription")
    if not raw:
        return None
    return json.loads(raw)


# =====================================================
# CHECK IF SUBSCRIPTION IS ACTIVE
# =====================================================
def is_subscription_active(customer_id: str):
    sub = get_subscription(customer_id)
    if not sub:
        return False

    now = int(time.time())

    if sub["expires_at"] < now:
        return False

    if sub["minutes_left"] <= 0:
        return False

    return True


# =====================================================
# CONSUME MINUTES (ON CALL END)
# =====================================================
def consume_minutes(customer_id: str, minutes: int):
    sub = get_subscription(customer_id)
    if not sub:
        return False

    sub["minutes_left"] = max(0, sub["minutes_left"] - minutes)

    redis_db.set(
        f"customer:{customer_id}:subscription",
        json.dumps(sub)
    )

    return True


# =====================================================
# AUTO RENEW SUBSCRIPTION (WALLET BASED)
# =====================================================
def try_auto_renew(customer_id: str, deduct_wallet_fn):
    """
    deduct_wallet_fn(customer_id, amount) -> True / False
    """

    sub = get_subscription(customer_id)
    if not sub or not sub.get("auto_renew"):
        return False

    now = int(time.time())
    expired = sub["expires_at"] <= now
    no_minutes = sub["minutes_left"] <= 0

    if not expired and not no_minutes:
        return False

    plans_raw = redis_db.get("sub:plans")
    if not plans_raw:
        return False

    plans = json.loads(plans_raw)
    plan = plans.get(sub["plan_id"])
    if not plan:
        return False

    price = float(plan.get("price", 0))
    minutes = int(plan.get("minutes", 0))
    validity_days = int(plan.get("validity_days", 0))

    # ---------- WALLET DEDUCTION ----------
    if not deduct_wallet_fn(customer_id, price):
        return False

    # ---------- RENEW ----------
    sub["minutes_left"] = minutes
    sub["expires_at"] = now + validity_days * 86400

    redis_db.set(
        f"customer:{customer_id}:subscription",
        json.dumps(sub)
    )

    # ---------- ADMIN REVENUE ----------
    redis_db.incrbyfloat(
        "admin:revenue:subscription",
        price
    )

    redis_db.hincrby(
        "admin:subscription:sales",
        sub["plan_id"],
        1
    )

    return True


# =====================================================
# ADMIN: SET / UPDATE PLANS (DYNAMIC)
# =====================================================
def set_plans(plans: dict):
    """
    Example:
    {
      "basic": {"price": 999, "minutes": 500, "validity_days": 30},
      "pro":   {"price": 2999, "minutes": 2000, "validity_days": 30}
    }
    """
    redis_db.set("sub:plans", json.dumps(plans))
    return True


# =====================================================
# ADMIN: GET ALL PLANS
# =====================================================
def get_plans():
    raw = redis_db.get("sub:plans")
    if not raw:
        return {}
    return json.loads(raw)
