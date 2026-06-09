"""Shared async HTTP client for outbound requests."""

from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(follow_redirects=False)
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def reset_http_client() -> None:
    """Reset client reference — used in tests."""
    global _client
    _client = None
