"""Area template library on disk (1.3.1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from campaign_rpg_engine import (
    Session,
    export_area_template,
    spawn_area_from_template,
    validate_area_template,
)

from backend.snapshot_compat import normalize_state_snapshot

_STUDIO_DIR = Path(__file__).resolve().parent.parent
AREA_TEMPLATES_DIR = _STUDIO_DIR / "area_templates"
_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*\.json$")


def _ensure_templates_dir() -> Path:
    AREA_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return AREA_TEMPLATES_DIR


def _sanitize_filename(name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", (name or "").strip()).strip("-._")
    if not stem:
        stem = "area-template"
    if not stem.lower().endswith(".json"):
        stem = f"{stem}.json"
    return stem


def _template_path(filename: str) -> Path:
    cleaned = _sanitize_filename(filename)
    if not _FILENAME_RE.match(cleaned):
        raise ValueError("Invalid template filename.")
    path = (_ensure_templates_dir() / cleaned).resolve()
    root = _ensure_templates_dir().resolve()
    if path.parent != root:
        raise ValueError("Invalid template path.")
    return path


def _read_template_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Template file must contain a JSON object.")
    err = validate_area_template(data)
    if err:
        raise ValueError(err)
    return data


def _serialize_list_entry(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    grid = data.get("grid") if isinstance(data.get("grid"), dict) else {}
    width = None
    height = None
    if grid:
        try:
            width = int(grid["max_x"]) - int(grid["min_x"]) + 1
            height = int(grid["max_y"]) - int(grid["min_y"]) + 1
        except (KeyError, TypeError, ValueError):
            width = None
            height = None
    return {
        "id": path.stem,
        "filename": path.name,
        "kind": "area",
        "name": str(data.get("name", "")),
        "grid_width": width,
        "grid_height": height,
        "object_count": len(data.get("objects") or []),
        "decoration_count": len(data.get("decorations") or []),
        "include_hidden_objects": bool(data.get("include_hidden_objects", True)),
    }


def list_area_templates() -> dict[str, object]:
    root = _ensure_templates_dir()
    templates: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = _read_template_file(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        templates.append(_serialize_list_entry(path, data))
    return {"ok": True, "templates": templates}


def get_area_template(template_id: str) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    try:
        data = _read_template_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "template": data, "meta": _serialize_list_entry(path, data)}


def save_area_template(template: dict[str, Any], *, filename: str) -> dict[str, object]:
    err = validate_area_template(template)
    if err:
        return {"ok": False, "message": err}
    path = _template_path(filename)
    path.write_text(json.dumps(template, indent=2), encoding="utf-8")
    data = _read_template_file(path)
    return {
        "ok": True,
        "message": f"Saved template {path.name!r}.",
        "meta": _serialize_list_entry(path, data),
    }


def delete_area_template(template_id: str) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    path.unlink()
    return {"ok": True, "message": f"Deleted template {path.name!r}."}


def export_area_template_from_world(
    session: Session,
    *,
    area_id: str,
    name: str | None = None,
    include_hidden_objects: bool = True,
) -> dict[str, object]:
    cleaned = (area_id or "").strip() or session.active_area_id
    if cleaned not in session.areas:
        return {"ok": False, "message": f"Unknown area {cleaned!r}."}
    try:
        template = export_area_template(
            session,
            cleaned,
            name=name,
            include_hidden_objects=include_hidden_objects,
        )
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "template": template}


def save_area_from_world(
    session: Session,
    *,
    area_id: str,
    filename: str,
    name: str | None = None,
    include_hidden_objects: bool = True,
) -> dict[str, object]:
    exported = export_area_template_from_world(
        session,
        area_id=area_id,
        name=name,
        include_hidden_objects=include_hidden_objects,
    )
    if not exported.get("ok"):
        return exported
    template = exported["template"]
    assert isinstance(template, dict)
    saved = save_area_template(template, filename=filename)
    if not saved.get("ok"):
        return saved
    return {
        "ok": True,
        "message": saved.get("message", "Saved."),
        "meta": saved.get("meta"),
    }


def spawn_area_template(
    session: Session,
    template_id: str,
    *,
    area_id: str,
    mode: str = "new",
) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    try:
        template = _read_template_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "message": str(exc)}
    return spawn_area_from_template_data(
        session,
        template,
        area_id=area_id,
        mode=mode,
    )


def spawn_area_from_template_data(
    session: Session,
    template: dict[str, Any],
    *,
    area_id: str,
    mode: str = "new",
) -> dict[str, object]:
    err = validate_area_template(template)
    if err:
        return {"ok": False, "message": err}
    cleaned_area_id = (area_id or "").strip()
    if not cleaned_area_id:
        return {"ok": False, "message": "area_id is required."}
    normalized_mode = (mode or "new").strip().lower()
    if normalized_mode not in ("new", "replace"):
        return {"ok": False, "message": "mode must be 'new' or 'replace'."}

    result = spawn_area_from_template(
        session,
        template,
        area_id=cleaned_area_id,
        mode=normalized_mode,  # type: ignore[arg-type]
    )
    if not result.ok:
        return {"ok": False, "message": result.message}
    return {
        "ok": True,
        "message": result.message,
        "area_id": result.area_id,
        "snapshot": normalize_state_snapshot(
            session.snapshot(include_private=True)
        ),
    }


def export_area_template_download(
    session: Session,
    *,
    area_id: str,
    filename: str,
    name: str | None = None,
    include_hidden_objects: bool = True,
) -> dict[str, object]:
    exported = export_area_template_from_world(
        session,
        area_id=area_id,
        name=name,
        include_hidden_objects=include_hidden_objects,
    )
    if not exported.get("ok"):
        return exported
    template = exported["template"]
    assert isinstance(template, dict)
    return {
        "ok": True,
        "filename": _sanitize_filename(filename),
        "template": template,
    }


def download_area_template_file(template_id: str) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    try:
        data = _read_template_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "filename": path.name, "template": data}
