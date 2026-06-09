from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import build_services, get_db_session
from app.models.domain import WebhookDeliveryResponse

router = APIRouter()


@router.get("/deliveries", response_model=list[WebhookDeliveryResponse])
def list_deliveries(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    include_payload: bool = Query(default=False),
    session: Session = Depends(get_db_session),
) -> list[WebhookDeliveryResponse]:
    services = build_services(session)
    deliveries = services["webhook_repo"].list_deliveries(limit=limit, offset=offset)
    return [
        WebhookDeliveryResponse(
            id=delivery.id,
            alert_id=delivery.alert_id,
            target_url=delivery.target_url,
            payload=delivery.payload_json if include_payload else {},
            status_code=delivery.status_code,
            success=delivery.success,
            attempt=delivery.attempt,
            error_message=delivery.error_message,
            delivered_at=delivery.delivered_at,
        )
        for delivery in deliveries
    ]
