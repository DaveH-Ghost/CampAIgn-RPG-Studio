"""Listen bind + public base URL for remote player join links (Studio 1.7.4)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765

# In-memory override (Settings). None = fall through to env / request.
_public_base_url_override: str | None = None

_UNUSABLE_JOIN_HOSTS = frozenset({"0.0.0.0", "::", "[::]"})


def listen_host() -> str:
    raw = (os.environ.get("CAMPAIGN_STUDIO_HOST") or "").strip()
    return raw or _DEFAULT_HOST


def listen_port() -> int:
    raw = (os.environ.get("CAMPAIGN_STUDIO_PORT") or "").strip()
    if not raw:
        return _DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        return _DEFAULT_PORT
    if port < 1 or port > 65535:
        return _DEFAULT_PORT
    return port


def _normalize_public_base(url: str) -> str:
    return url.strip().rstrip("/")


def _env_public_base_url() -> str:
    return _normalize_public_base(os.environ.get("CAMPAIGN_STUDIO_PUBLIC_URL") or "")


def get_public_base_url() -> str:
    """Configured public base (Settings override, else env). Empty if unset."""
    if _public_base_url_override is not None:
        return _normalize_public_base(_public_base_url_override)
    return _env_public_base_url()


def set_public_base_url(url: str | None) -> dict[str, Any]:
    """
    Set in-memory public base URL for this process.

    Pass ``None`` or ``\"\"`` to clear the override (env still applies if set).
    """
    global _public_base_url_override
    if url is None or not str(url).strip():
        _public_base_url_override = None
        return get_hosting_settings()
    cleaned = _normalize_public_base(str(url))
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {
            "ok": False,
            "message": "Public base URL must be an absolute http(s) URL "
            "(e.g. https://campaign.example.com).",
        }
    if (parsed.hostname or "").lower() in _UNUSABLE_JOIN_HOSTS:
        return {
            "ok": False,
            "message": "Public base URL cannot use 0.0.0.0 or :: — use a reachable host or domain.",
        }
    _public_base_url_override = cleaned
    return get_hosting_settings()


def reset_hosting_for_tests() -> None:
    """Clear in-memory public URL override (tests)."""
    global _public_base_url_override
    _public_base_url_override = None


def get_hosting_settings() -> dict[str, Any]:
    public = get_public_base_url()
    return {
        "ok": True,
        "listen_host": listen_host(),
        "listen_port": listen_port(),
        "public_base_url": public,
        "public_base_url_from_env": _env_public_base_url(),
        "join_link_hint": (
            f"{public}/play/generic/?seat=…"
            if public
            else "Uses the address in your browser when you copy a join link "
            "(or set Public base URL / CAMPAIGN_STUDIO_PUBLIC_URL)."
        ),
        "remote_hint": (
            "To accept remote players, start Studio with --host 0.0.0.0 "
            "(or CAMPAIGN_STUDIO_HOST=0.0.0.0). Requires a restart."
        ),
    }


def resolve_join_base(request_base_url: str) -> tuple[str | None, str | None]:
    """
    Return ``(base, error)`` for player join links.

    Prefers configured public base URL; otherwise the request base URL.
    Rejects unusable hosts like ``0.0.0.0``.
    """
    configured = get_public_base_url()
    if configured:
        return configured, None

    base = str(request_base_url or "").rstrip("/")
    if not base:
        return None, "Could not determine join link host. Set Public base URL in Settings."
    parsed = urlparse(base if "://" in base else f"http://{base}")
    host = (parsed.hostname or "").lower()
    if host in _UNUSABLE_JOIN_HOSTS:
        return (
            None,
            "Server is listening on all interfaces; set Public base URL in Settings "
            "(or CAMPAIGN_STUDIO_PUBLIC_URL) to a reachable host so player links work.",
        )
    return base, None
