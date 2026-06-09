"""Short-lived cache for AI analysis results keyed by input payload hash."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

_cache: dict[str, tuple[float, Any]] = {}
_MAX_CACHE_ENTRIES = 500


def payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def get_cached(key: str, *, ttl_seconds: int) -> Any | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    stored_at, value = entry
    if time.monotonic() - stored_at > ttl_seconds:
        _cache.pop(key, None)
        return None
    return value


def set_cached(key: str, value: Any) -> None:
    if len(_cache) >= _MAX_CACHE_ENTRIES:
        oldest_key = min(_cache, key=lambda item: _cache[item][0])
        _cache.pop(oldest_key, None)
    _cache[key] = (time.monotonic(), value)


def clear_ai_cache() -> None:
    _cache.clear()
