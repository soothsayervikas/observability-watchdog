from unittest.mock import patch

import pytest

from app.core.exceptions import ConfigurationError
from app.core.url_safety import validate_webhook_url


@patch("app.core.url_safety.socket.getaddrinfo")
def test_validate_webhook_url_blocks_dns_rebinding_to_private_ip(mock_getaddrinfo) -> None:
    mock_getaddrinfo.return_value = [
        (2, 1, 6, "", ("10.0.0.5", 0)),
    ]
    with pytest.raises(ConfigurationError, match="resolves to blocked address"):
        validate_webhook_url("https://evil.example.com/webhook", allow_private_hosts=False)


@patch("app.core.url_safety.socket.getaddrinfo")
def test_validate_webhook_url_allows_public_resolved_ip(mock_getaddrinfo) -> None:
    mock_getaddrinfo.return_value = [
        (2, 1, 6, "", ("93.184.216.34", 0)),
    ]
    url = validate_webhook_url("https://hooks.example.com/webhook", allow_private_hosts=False)
    assert url == "https://hooks.example.com/webhook"
