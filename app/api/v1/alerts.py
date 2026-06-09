from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import build_services, get_db_session
from app.core.exceptions import AlertNotFoundError, WatchdogError
from app.models.domain import AlertResponse, AlertSeverity, AlertStatus, AlertStatusUpdate

router = APIRouter()


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    severity: AlertSeverity | None = None,
    status: AlertStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[AlertResponse]:
    services = build_services(session)
    alerts = services["alert_repo"].list_alerts(
        severity=severity.value if severity else None,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [services["alerts"].to_response(alert) for alert in alerts]


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    session: Session = Depends(get_db_session),
) -> AlertResponse:
    services = build_services(session)
    try:
        return services["alerts"].update_status(alert_id, payload.status)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WatchdogError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
