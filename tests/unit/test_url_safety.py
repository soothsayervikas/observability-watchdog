from unittest.mock import patch

import pytest

from app.core.exceptions import ConfigurationError
from app.core.url_safety import pin_webhook_target, validate_webhook_url


@patch("app.core.url_safety.socket.getaddrinfo")
def test_validate_webhook_url_allows_public_https(mock_getaddrinfo) -> None:
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
    url = validate_webhook_url("https://hooks.example.com/alerts", allow_private_hosts=False)
    assert url == "https://hooks.example.com/alerts"


def test_validate_webhook_url_blocks_localhost_in_strict_mode() -> None:
    with pytest.raises(ConfigurationError):
        validate_webhook_url("http://127.0.0.1:8765/webhook", allow_private_hosts=False)


def test_validate_webhook_url_allows_localhost_in_relaxed_mode() -> None:
    url = validate_webhook_url("http://127.0.0.1:8765/webhook", allow_private_hosts=True)
    assert url.startswith("http://127.0.0.1")


def test_validate_webhook_url_rejects_non_http_scheme() -> None:
    with pytest.raises(ConfigurationError):
        validate_webhook_url("ftp://hooks.example.com/x", allow_private_hosts=False)


@patch("app.core.url_safety.socket.getaddrinfo")
def test_pin_webhook_target_uses_resolved_ip(mock_getaddrinfo) -> None:
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
    pinned = pin_webhook_target("https://hooks.example.com/alerts", allow_private_hosts=False)
    assert pinned.request_url == "https://93.184.216.34:443/alerts"
    assert pinned.host_header == "hooks.example.com"
