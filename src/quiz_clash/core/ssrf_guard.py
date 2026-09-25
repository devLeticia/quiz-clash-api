# src/quiz_clash/core/ssrf_guard.py
import ipaddress
import socket
from urllib.parse import urlparse

from quiz_clash.core.exceptions import URLProcessingError

ALLOWED_SCHEMES = {"http", "https"}


def _is_private_or_reserved(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_url_is_safe(url: str) -> None:
    """Reject non-http(s) schemes and URLs that resolve to a private,
    loopback, link-local, or otherwise reserved IP address (SSRF guard)."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise URLProcessingError(f"URL scheme '{parsed.scheme}' is not allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise URLProcessingError("URL is missing a hostname.")

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise URLProcessingError(f"Could not resolve host '{hostname}': {e}") from e

    for _, _, _, _, sockaddr in resolved:
        ip_str = sockaddr[0]
        if _is_private_or_reserved(ip_str):
            raise URLProcessingError(
                "URL resolves to a private/internal address and is not allowed."
            )
