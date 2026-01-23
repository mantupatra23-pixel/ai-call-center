# services/call_timer_service.py

import time
import json
from db.redis import redis_db

from services.billing_service import deduct_balance
from services.subscription_service import (
    get_subscription,
    is_subscription_active,
)
from services.auto_renew_service import try_auto_renew

CHECK_INTERVAL = 60  # seconds (1 minute)


def start_call_timer(call_sid: str, customer_id: str):
    """
    Runs during live call.
    Priority:
    1. Active subscription minutes
    2. Auto-renew subscription
    3. Wallet deduction
    4. Force hangup when balance = 0
    """

    while True:
        time.sleep(CHECK_INTERVAL)

        now = int(time.time())

        # =====================================================
        # 1️⃣ CHECK SUBSCRIPTION (REAL-TIME)
        # =====================================================
        sub = get_subscription(customer_id)

        if sub:
            # ---------- EXPIRED ----------
            if sub.get("expires_at", 0) < now:
                redis_db.delete(f"customer:{customer_id}:subscription")

            # ---------- MINUTES AVAILABLE ----------
            elif sub.get("minutes_left", 0) > 0:
                sub["minutes_left"] -= 1

                redis_db.set(
                    f"customer:{customer_id}:subscription",
                    json.dumps(sub)
                )

                # ✅ Subscription minute used
                continue

            # ---------- MINUTES FINISHED → TRY AUTO-RENEW ----------
            else:
                renewed = try_auto_renew(customer_id)
                if renewed:
                    continue
                else:
                    redis_db.set(
                        f"call:hangup:{call_sid}",
                        "1"
                    )
                    break

        # =====================================================
        # 2️⃣ NO SUBSCRIPTION → WALLET DEDUCTION
        # =====================================================
        config_raw = redis_db.get("admin:config")
        if not config_raw:
            # Safety fallback
            redis_db.set(f"call:hangup:{call_sid}", "1")
            break

        try:
            config = json.loads(config_raw)
        except Exception:
            redis_db.set(f"call:hangup:{call_sid}", "1")
            break

        rate = float(config.get("call_rate_per_min", 0))

        if rate <= 0:
            redis_db.set(f"call:hangup:{call_sid}", "1")
            break

        # Deduct wallet balance
        balance = deduct_balance(customer_id, rate)

        # =====================================================
        # 3️⃣ BALANCE ZERO → FORCE HANGUP
        # =====================================================
        if balance <= 0:
            redis_db.set(
                f"call:hangup:{call_sid}",
                "1"
            )
            break
