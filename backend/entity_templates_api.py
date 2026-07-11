"""Entity template library on disk (1.2.1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from campaign_rpg_engine import (
    Session,
    export_agent_template,
    export_object_template,
    spawn_agent_from_template,
    spawn_object_from_template,
    validate_template,
)
from campaign_rpg_engine.world_edit_api import find_object_in_session

from backend.snapshot_compat import normalize_state_snapshot

_STUDIO_DIR = Path(__file__).resolve().parent.parent
ENTITY_TEMPLATES_DIR = _STUDIO_DIR / "entity_templates"
_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*\.json$")


def _ensure_templates_dir() -> Path:
    ENTITY_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return ENTITY_TEMPLATES_DIR


def _sanitize_filename(name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", (name or "").strip()).strip("-._")
    if not stem:
        stem = "template"
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
    err = validate_template(data)
    if err:
        raise ValueError(err)
    return data


def _serialize_list_entry(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": path.stem,
        "filename": path.name,
        "kind": str(data.get("kind", "")),
        "name": str(data.get("name", "")),
        "include_memory": bool(data.get("include_memory")),
    }


def list_entity_templates() -> dict[str, object]:
    root = _ensure_templates_dir()
    templates: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = _read_template_file(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        templates.append(_serialize_list_entry(path, data))
    return {"ok": True, "templates": templates}


def get_entity_template(template_id: str) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    try:
        data = _read_template_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "template": data, "meta": _serialize_list_entry(path, data)}


def save_entity_template(template: dict[str, Any], *, filename: str) -> dict[str, object]:
    err = validate_template(template)
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


def delete_entity_template(template_id: str) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    path.unlink()
    return {"ok": True, "message": f"Deleted template {path.name!r}."}


def export_entity_template(
    session: Session,
    *,
    kind: str,
    entity_id: str,
    include_memory: bool = False,
) -> dict[str, object]:
    kind = (kind or "").strip().lower()
    entity_id = (entity_id or "").strip()
    if kind == "object":
        located = find_object_in_session(session, entity_id)
        if located is None:
            return {"ok": False, "message": f"Object {entity_id!r} not found."}
        _area_id, _area, obj = located
        template = export_object_template(obj)
    elif kind == "agent":
        agent = session.get_agent(entity_id)
        if agent is None:
            return {"ok": False, "message": f"Agent {entity_id!r} not found."}
        template = export_agent_template(agent, include_memory=include_memory)
    else:
        return {"ok": False, "message": "kind must be 'object' or 'agent'."}
    return {"ok": True, "template": template}


def save_entity_from_world(
    session: Session,
    *,
    kind: str,
    entity_id: str,
    filename: str,
    include_memory: bool = False,
) -> dict[str, object]:
    exported = export_entity_template(
        session,
        kind=kind,
        entity_id=entity_id,
        include_memory=include_memory,
    )
    if not exported.get("ok"):
        return exported
    template = exported["template"]
    assert isinstance(template, dict)
    saved = save_entity_template(template, filename=filename)
    if not saved.get("ok"):
        return saved
    return {
        "ok": True,
        "message": saved.get("message", "Saved."),
        "meta": saved.get("meta"),
    }


def spawn_entity_template(
    session: Session,
    template_id: str,
    *,
    position: list[int] | tuple[int, int],
    area_id: str | None = None,
) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    try:
        template = _read_template_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "message": str(exc)}
    return spawn_entity_from_template_data(
        session,
        template,
        position=position,
        area_id=area_id,
    )


def spawn_entity_from_template_data(
    session: Session,
    template: dict[str, Any],
    *,
    position: list[int] | tuple[int, int],
    area_id: str | None = None,
) -> dict[str, object]:
    err = validate_template(template)
    if err:
        return {"ok": False, "message": err}

    if not isinstance(position, (list, tuple)) or len(position) != 2:
        return {"ok": False, "message": "position must be [x, y]."}
    pos = (int(position[0]), int(position[1]))
    resolved_area = (area_id or "").strip() or session.active_area_id

    kind = template.get("kind")
    if kind == "object":
        result = spawn_object_from_template(
            session, template, pos, area_id=resolved_area
        )
    elif kind == "agent":
        result = spawn_agent_from_template(
            session, template, pos, area_id=resolved_area
        )
    else:
        return {"ok": False, "message": "Template kind must be 'object' or 'agent'."}

    if not result.ok:
        return {"ok": False, "message": result.message}
    return {
        "ok": True,
        "message": result.message,
        "kind": kind,
        "entity_id": (
            result.object.id if result.object is not None else result.agent.id if result.agent else ""
        ),
        "snapshot": normalize_state_snapshot(
            session.snapshot(include_private=True)
        ),
    }


def export_entity_template_download(
    session: Session,
    *,
    kind: str,
    entity_id: str,
    filename: str,
    include_memory: bool = False,
) -> dict[str, object]:
    exported = export_entity_template(
        session,
        kind=kind,
        entity_id=entity_id,
        include_memory=include_memory,
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


def download_entity_template_file(template_id: str) -> dict[str, object]:
    path = _template_path(f"{template_id}.json")
    if not path.is_file():
        return {"ok": False, "message": f"Template {template_id!r} not found."}
    try:
        data = _read_template_file(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "filename": path.name, "template": data}
