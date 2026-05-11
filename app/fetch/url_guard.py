from __future__ import annotations

import ipaddress
import socket
from typing import Callable
from urllib.parse import urlsplit


class UnsafeUrlError(ValueError):
    pass


_ALLOWED_SCHEMES = {"http", "https"}
_LOCAL_HOST_ALIASES = {"localhost", "localhost.localdomain"}

Resolver = Callable[..., list[tuple[object, object, object, object, tuple[object, ...]]]]


def validate_public_http_url(
    url: str,
    *,
    require_dns_resolution: bool = True,
    resolver: Resolver | None = None,
) -> str:
    candidate = url.strip()
    if not candidate:
        raise UnsafeUrlError("URL is empty")

    parsed = urlsplit(candidate)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Unsupported URL scheme: {scheme or 'missing'}")

    if parsed.username or parsed.password:
        raise UnsafeUrlError("URL must not contain embedded credentials")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeUrlError("URL host is missing")

    lowered_host = hostname.lower().rstrip(".")
    if lowered_host in _LOCAL_HOST_ALIASES:
        raise UnsafeUrlError(f"Blocked local hostname target: {hostname}")

    ip_literal = _try_parse_ip(hostname)
    if ip_literal is not None:
        _assert_public_ip(ip_literal, hostname)
        return candidate

    if not require_dns_resolution:
        return candidate

    lookup = resolver or socket.getaddrinfo
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        resolved = lookup(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UnsafeUrlError(f"DNS resolution failed for host={hostname}") from exc

    addresses: set[str] = set()
    for entry in resolved:
        sockaddr = entry[4]
        if not isinstance(sockaddr, tuple) or not sockaddr:
            continue
        addr = str(sockaddr[0])
        addresses.add(addr)

    if not addresses:
        raise UnsafeUrlError(f"No resolved addresses found for host={hostname}")

    for address in sorted(addresses):
        ip_obj = _try_parse_ip(address)
        if ip_obj is None:
            raise UnsafeUrlError(f"Resolved non-IP address for host={hostname}")
        _assert_public_ip(ip_obj, f"{hostname} -> {address}")

    return candidate


def _try_parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _assert_public_ip(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address, label: str) -> None:
    if ip_obj.is_loopback:
        raise UnsafeUrlError(f"Blocked loopback target: {label}")
    if ip_obj.is_private:
        raise UnsafeUrlError(f"Blocked private-network target: {label}")
    if ip_obj.is_link_local:
        raise UnsafeUrlError(f"Blocked link-local target: {label}")
    if ip_obj.is_multicast:
        raise UnsafeUrlError(f"Blocked multicast target: {label}")
    if ip_obj.is_reserved:
        raise UnsafeUrlError(f"Blocked reserved target: {label}")
    if ip_obj.is_unspecified:
        raise UnsafeUrlError(f"Blocked unspecified target: {label}")
    if getattr(ip_obj, "is_site_local", False):
        raise UnsafeUrlError(f"Blocked site-local target: {label}")
    if not ip_obj.is_global:
        raise UnsafeUrlError(f"Blocked non-global target: {label}")
