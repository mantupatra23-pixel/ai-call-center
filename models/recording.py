from pydantic import BaseModel

class Recording(BaseModel):
    recording_sid: str
    call_sid: str
    customer_id: str
    recording_url: str
    duration_sec: int
