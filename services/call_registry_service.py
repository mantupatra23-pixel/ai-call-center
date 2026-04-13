import time
import json
from db.redis import redis_db

# ==========================================
# REGISTER CALL START
# ==========================================
def register_call_start(customer_id: str, call_sid: str = ""):
    """Call start hote hi registry me entry"""
    data = {
        "customer_id": customer_id,
        "call_sid": call_sid,
        "started_at": int(time.time()),
        "status": "active"
    }

    # Agar call_sid aayi hai toh hi us naam se save karo
    if call_sid:
        redis_db.set(f"call:{call_sid}", json.dumps(data))

    # active calls counter (safety / analytics)
    redis_db.incr(f"customer:{customer_id}:active_calls")
    
    return data

# ==========================================
# GET CALL INFO
# ==========================================
def get_call(call_sid: str):
    raw = redis_db.get(f"call:{call_sid}")
    if not raw:
        return None
        
    try:
        return json.loads(raw)
    except Exception:
        return None

# ==========================================
# DELETE CALL (Webhook isko dhoondh raha tha)
# ==========================================
def delete_call(call_sid: str):
    """Call registry aur active list se hatane ke liye cleanup"""
    call = get_call(call_sid)
    if call and "customer_id" in call:
        customer_id = call["customer_id"]
        # Active counter kam karo taaki user naya call laga sake
        redis_db.decr(f"customer:{customer_id}:active_calls")
        
    redis_db.delete(f"call:{call_sid}")
    return True

# ==========================================
# REGISTER CALL END
# ==========================================
def register_call_end(call_sid: str, duration_sec: int = 0):
    """Call end hone par cleanup + history"""
    call = get_call(call_sid)
    if not call:
        return None
        
    customer_id = call.get("customer_id")
    if not customer_id:
        return None

    # active calls decrement
    redis_db.decr(f"customer:{customer_id}:active_calls")

    ended_at = int(time.time())
    
    history = {
        "call_sid": call_sid,
        "customer_id": customer_id,
        "started_at": call.get("started_at", ended_at),
        "ended_at": ended_at,
        "duration_sec": duration_sec
    }

    # push history
    redis_db.lpush(
        f"customer:{customer_id}:call_history", 
        json.dumps(history)
    )

    # remove active call registry
    redis_db.delete(f"call:{call_sid}")
    
    return history
