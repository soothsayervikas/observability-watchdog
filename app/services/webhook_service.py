import asyncio

import httpx

from app.config import Settings
from app.core.exceptions import ConfigurationError, WebhookDeliveryError
from app.core.http_client import get_http_client
from app.core.logging import get_logger, request_id_var
from app.core.metrics import WEBHOOK_DELIVERIES
from app.core.url_safety import pin_webhook_target
from app.core.webhook_signing import sign_webhook_payload
from app.models.db import AlertORM, WebhookDeliveryORM
from app.repositories.log_repository import WebhookRepository

logger = get_logger(__name__)


class WebhookService:
    def __init__(self, settings: Settings, webhook_repo: WebhookRepository) -> None:
        self._settings = settings
        self._webhook_repo = webhook_repo

    async def dispatch_alert(self, alert: AlertORM) -> WebhookDeliveryORM:
        try:
            pinned = pin_webhook_target(
                self._settings.webhook_url,
                allow_private_hosts=self._settings.webhook_allow_private_hosts,
            )
        except ConfigurationError as exc:
            raise WebhookDeliveryError(str(exc)) from exc

        trace_id = request_id_var.get()
        payload = {
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "detected_at": alert.detected_at.isoformat() + "Z",
            "metrics": alert.metrics_json,
            "source": self._settings.app_name,
            "trace_id": trace_id,
        }

        headers = {"X-Alert-Id": alert.id, "Content-Type": "application/json"}
        if pinned.host_header:
            headers["Host"] = pinned.host_header
        if self._settings.hardening_enabled and self._settings.webhook_hmac_secret:
            signature = sign_webhook_payload(self._settings.webhook_hmac_secret, payload)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        last_delivery: WebhookDeliveryORM | None = None
        max_retries = self._settings.webhook_max_retries
        target_url = self._settings.webhook_url.strip()

        for attempt in range(1, max_retries + 1):
            try:
                timeout = httpx.Timeout(
                    self._settings.webhook_timeout_seconds,
                    connect=min(5.0, self._settings.webhook_timeout_seconds),
                )
                client = get_http_client()
                response = await client.post(
                    pinned.request_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )
                delivery = WebhookDeliveryORM(
                    alert_id=alert.id,
                    target_url=target_url,
                    payload_json=payload,
                    status_code=response.status_code,
                    success=200 <= response.status_code < 300,
                    attempt=attempt,
                    error_message=None if response.is_success else response.text[:500],
                )
                last_delivery = self._webhook_repo.create(delivery)
                WEBHOOK_DELIVERIES.inc(success="true" if delivery.success else "false")
                if delivery.success:
                    logger.info("Webhook delivered for alert %s (attempt %s)", alert.id, attempt)
                    return delivery
            except httpx.HTTPError as exc:
                last_delivery = self._webhook_repo.create(
                    WebhookDeliveryORM(
                        alert_id=alert.id,
                        target_url=target_url,
                        payload_json=payload,
                        status_code=None,
                        success=False,
                        attempt=attempt,
                        error_message=str(exc)[:500],
                    )
                )
                WEBHOOK_DELIVERIES.inc(success="false")
                logger.warning(
                    "Webhook failed for alert %s (attempt %s): %s", alert.id, attempt, str(exc)
                )

            if attempt < max_retries:
                delay = self._settings.webhook_retry_base_seconds * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

        if last_delivery is None:
            raise WebhookDeliveryError("Webhook delivery failed without recording attempts")

        raise WebhookDeliveryError(
            f"Webhook delivery failed for alert {alert.id} after {max_retries} attempts"
        )
