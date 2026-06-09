from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def sign_webhook_payload(secret: str, payload: dict[str, Any]) -> str:
    """Return HMAC-SHA256 hex digest for a JSON webhook payload."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_webhook_signature(secret: str, payload: dict[str, Any], signature: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = sign_webhook_payload(secret, payload)
    provided = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)
