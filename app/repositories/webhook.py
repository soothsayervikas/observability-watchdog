from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db import WebhookDeliveryORM


class WebhookRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, delivery: WebhookDeliveryORM) -> WebhookDeliveryORM:
        self._session.add(delivery)
        self._session.commit()
        self._session.refresh(delivery)
        return delivery

    def list_deliveries(self, *, limit: int = 50, offset: int = 0) -> Sequence[WebhookDeliveryORM]:
        return self._session.scalars(
            select(WebhookDeliveryORM)
            .order_by(WebhookDeliveryORM.delivered_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
