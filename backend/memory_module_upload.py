"""Custom memory module upload for campaign-rpg-studio (V0.4.6)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from campaign_rpg_engine import (
    register_memory_module_from_path,
    register_memory_module_from_source,
)

_STUDIO_DIR = Path(__file__).resolve().parent.parent
CUSTOM_MODULES_DIR = _STUDIO_DIR / ".custom_modules"


def load_cached_custom_modules() -> list[str]:
    """Register every cached .py module (survives uvicorn dev reload)."""
    if not CUSTOM_MODULES_DIR.is_dir():
        return []
    loaded: list[str] = []
    for path in sorted(CUSTOM_MODULES_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module_id = register_memory_module_from_path(path)
        except (OSError, ValueError, TypeError):
            continue
        loaded.append(module_id)
    return loaded


def upload_memory_module(*, source: str, filename: str) -> dict[str, Any]:
    module_id = register_memory_module_from_source(
        source,
        filename=filename,
        cache_dir=CUSTOM_MODULES_DIR,
    )
    return {
        "ok": True,
        "module_id": module_id,
        "message": f"Loaded memory module {module_id!r}.",
    }
