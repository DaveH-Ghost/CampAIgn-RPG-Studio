"""Package version helpers for campaign-rpg-studio."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

STUDIO_TAGLINE = "CampAIgn RPG Studio"


def studio_version() -> str:
    try:
        return version("campaign-rpg-studio")
    except PackageNotFoundError:
        return "1.5.1"


def engine_version() -> str:
    try:
        from campaign_rpg_engine import __version__

        return __version__
    except Exception:
        return "unknown"


def banner_text() -> str:
    return f"V{studio_version()} — {STUDIO_TAGLINE}"
