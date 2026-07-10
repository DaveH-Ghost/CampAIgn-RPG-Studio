"""Package version helpers for realm-studio."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

STUDIO_TAGLINE = "Reference GM for realm-fabric"


def studio_version() -> str:
    try:
        return version("realm-studio")
    except PackageNotFoundError:
        return "1.0.0"


def engine_version() -> str:
    try:
        from realm_fabric import __version__

        return __version__
    except Exception:
        return "unknown"


def banner_text() -> str:
    return f"V{studio_version()} — {STUDIO_TAGLINE}"
