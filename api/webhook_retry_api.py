from fastapi import APIRouter
from services.webhook_retry_service import retry_failed_webhooks
from api.twilio_webhook_api import call_status

router = APIRouter(prefix="/admin/retry", tags=["Retry"])

@router.post("/webhooks")
def retry_webhooks():
    retry_failed_webhooks(call_status)
    return {"message": "Retry triggered"}
