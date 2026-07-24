"""Package version helpers for campaign-rpg-studio."""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

STUDIO_TAGLINE = "CampAIgn RPG Studio"
_ROOT = Path(__file__).resolve().parent.parent


def studio_version() -> str:
    """Prefer pyproject.toml (editable checkout) over possibly stale install metadata."""
    pyproject_path = _ROOT / "pyproject.toml"
    if pyproject_path.is_file():
        try:
            return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"][
                "version"
            ]
        except Exception:
            pass
    try:
        return version("campaign-rpg-studio")
    except PackageNotFoundError:
        return "1.7.4"


def engine_version() -> str:
    try:
        from campaign_rpg_engine import __version__

        return __version__
    except Exception:
        return "unknown"


def banner_text() -> str:
    return f"V{studio_version()} — {STUDIO_TAGLINE}"
