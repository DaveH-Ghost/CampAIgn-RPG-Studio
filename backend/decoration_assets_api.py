"""Decoration image uploads for campaign-rpg-studio (V1.3.0)."""

from __future__ import annotations

import re
from pathlib import Path

_ALLOWED_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"})
_MAX_BYTES = 10 * 1024 * 1024

_STUDIO_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = _STUDIO_DIR / "frontend" / "assets"


def _ensure_assets_dir() -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    return ASSETS_DIR


def _sanitize_filename(filename: str) -> str:
    stem = Path(filename).name
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem.strip()).strip("-._")
    if not stem:
        stem = "image.png"
    suffix = Path(stem).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise ValueError(
            "Image must be PNG, JPG, GIF, WebP, or SVG "
            f"(got {suffix!r})."
        )
    return stem


def _unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _find_duplicate_asset(data: bytes, assets_dir: Path) -> Path | None:
    """Return an existing asset file with identical bytes, if any."""
    for path in sorted(assets_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _ALLOWED_SUFFIXES:
            continue
        try:
            if path.read_bytes() == data:
                return path
        except OSError:
            continue
    return None


def upload_decoration_asset(*, data: bytes, filename: str) -> dict[str, object]:
    """Save an uploaded image under ``frontend/assets/`` and return its path."""
    if not data:
        raise ValueError("Uploaded file is empty.")
    if len(data) > _MAX_BYTES:
        raise ValueError("Image must be 10 MB or smaller.")

    safe_name = _sanitize_filename(filename)
    assets_dir = _ensure_assets_dir()

    duplicate = _find_duplicate_asset(data, assets_dir)
    if duplicate is not None:
        rel_path = f"assets/{duplicate.name}"
        return {
            "ok": True,
            "path": rel_path,
            "reused": True,
            "message": f"Using existing {rel_path}.",
        }

    dest = _unique_path(assets_dir, safe_name)
    dest.write_bytes(data)

    rel_path = f"assets/{dest.name}"
    return {
        "ok": True,
        "path": rel_path,
        "reused": False,
        "message": f"Saved image as {rel_path}.",
    }
