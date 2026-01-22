from pydantic import BaseModel
from typing import Optional

class CallLog(BaseModel):
    call_sid: str
    customer_id: str
    from_number: str
    to_number: str
    status: str              # initiated / ringing / answered / completed / failed
    duration_sec: int = 0
    cost: float = 0.0
    recording_url: Optional[str] = None
