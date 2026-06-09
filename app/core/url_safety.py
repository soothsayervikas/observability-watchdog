"""Validate outbound webhook URLs to reduce SSRF risk."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from app.core.exceptions import ConfigurationError

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
    }
)


def _ip_is_blocked(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _hostname_is_private(hostname: str) -> bool:
    lowered = hostname.lower().rstrip(".")
    if lowered in _BLOCKED_HOSTNAMES:
        return True
    if lowered.endswith(".internal"):
        return True

    try:
        addr = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return _ip_is_blocked(addr)


def _resolve_host_ips(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve hostname to IP addresses for connect-time SSRF validation."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ConfigurationError(f"WEBHOOK_URL hostname could not be resolved: {hostname}") from exc

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    seen: set[str] = set()
    for info in infos:
        raw = str(info[4][0])
        if raw in seen:
            continue
        seen.add(raw)
        try:
            addresses.append(ipaddress.ip_address(raw))
        except ValueError:
            continue

    if not addresses:
        raise ConfigurationError(
            f"WEBHOOK_URL hostname resolved to no usable addresses: {hostname}"
        )

    return addresses


def validate_webhook_url(url: str, *, allow_private_hosts: bool) -> str:
    """Return normalized URL or raise ConfigurationError."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ConfigurationError("WEBHOOK_URL must use http or https scheme")
    if not parsed.hostname:
        raise ConfigurationError("WEBHOOK_URL must include a hostname")

    hostname = parsed.hostname

    if not allow_private_hosts:
        if _hostname_is_private(hostname):
            raise ConfigurationError(
                "WEBHOOK_URL must not target private or loopback addresses in strict mode"
            )
        for addr in _resolve_host_ips(hostname):
            if _ip_is_blocked(addr):
                raise ConfigurationError(
                    f"WEBHOOK_URL resolves to blocked address {addr} in strict mode"
                )

    return url.strip()


@dataclass(frozen=True)
class PinnedWebhookTarget:
    """Connect URL with optional Host header to prevent DNS rebinding."""

    request_url: str
    host_header: str | None = None


def pin_webhook_target(url: str, *, allow_private_hosts: bool) -> PinnedWebhookTarget:
    """Validate URL and pin the first resolved IP for the outbound HTTP request."""
    normalized = validate_webhook_url(url, allow_private_hosts=allow_private_hosts)
    if allow_private_hosts:
        return PinnedWebhookTarget(request_url=normalized)

    parsed = urlparse(normalized)
    hostname = parsed.hostname
    if hostname is None:
        raise ConfigurationError("WEBHOOK_URL must include a hostname")

    addresses = _resolve_host_ips(hostname)
    addr = addresses[0]
    host_literal = f"[{addr}]" if addr.version == 6 else str(addr)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    pinned = urlunparse(
        (
            parsed.scheme,
            f"{host_literal}:{port}",
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return PinnedWebhookTarget(request_url=pinned, host_header=hostname)
