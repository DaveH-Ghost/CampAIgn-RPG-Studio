"""Lorebook API helpers for campaign-rpg-studio (V0.5.0)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from campaign_rpg_engine import (
    Lorebook,
    LorebookScanConfig,
    LoreEntry,
    Session,
    build_passive_vision,
    create_empty_lorebook,
    describe_scan_sources,
    load_lorebook_from_dict,
    load_lorebook_from_path,
    new_st_entry_dict,
    with_st_entry_defaults,
)


def _resolve_agent(session: Session, agent_id: str | None):
    if agent_id is not None:
        agent = session.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id!r} not found.")
        return agent
    return session.get_active_agent()


def get_lorebook_scan_config(session: Session, *, agent_id: str | None = None) -> dict[str, Any]:
    try:
        agent = _resolve_agent(session, agent_id)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    area = session.get_area_for_agent(agent)
    ctx = session.build_prompt_context_for_agent(agent.id)
    passive = build_passive_vision(
        agent,
        area,
        vision_units=session.vision_units,
        units_per_tile=session.vision_units_per_tile,
    )
    return {
        "ok": True,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "config": session.lorebook_scan_config.to_dict(),
        "sources": describe_scan_sources(
            agent=agent,
            area=area,
            memory_text=ctx.memory,
            passive_vision=passive,
            scan_config=session.lorebook_scan_config,
        ),
    }


def put_lorebook_scan_config(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "message": "Scan config must be an object."}
    current = session.lorebook_scan_config.to_dict()
    for key in LorebookScanConfig.__dataclass_fields__:
        if key in payload:
            current[key] = bool(payload[key])
    session.lorebook_scan_config = LorebookScanConfig.from_dict(current)
    return get_lorebook_scan_config(session)


def _studio_entry_to_st_shape(item: dict[str, Any]) -> dict[str, Any]:
    """Map campaign-rpg-studio editor payload to ST field names (disable-only)."""
    data = dict(item)
    if "disable" not in data:
        data["disable"] = not bool(data.pop("enabled", True))
    else:
        data.pop("enabled", None)
    if "keys" in data and "key" not in data:
        data["key"] = data.pop("keys")
    if "keys_secondary" in data and "keysecondary" not in data:
        data["keysecondary"] = data.pop("keys_secondary")
    if "selective_logic" in data and "selectiveLogic" not in data:
        data["selectiveLogic"] = data.pop("selective_logic")
    if "ignore_budget" in data and "ignoreBudget" not in data:
        data["ignoreBudget"] = data.pop("ignore_budget")
    return data


def _entry_from_payload(item: dict[str, Any], *, previous: LoreEntry | None) -> LoreEntry:
    shaped = _studio_entry_to_st_shape(item)
    if previous is not None:
        merged = dict(previous.raw)
        merged.update(shaped)
        shaped = merged
    else:
        uid = int(shaped.get("uid", 0))
        shaped = new_st_entry_dict(
            uid,
            order=int(shaped.get("order", 0)),
            display_index=shaped.get("displayIndex"),
            comment=str(shaped.get("comment", "New entry")),
            content=str(shaped.get("content", "")),
            keys=list(shaped.get("key") or []),
            keys_secondary=list(shaped.get("keysecondary") or []),
            disable=bool(shaped.get("disable", False)),
            constant=bool(shaped.get("constant", False)),
            selective=bool(shaped.get("selective", False)),
            selective_logic=int(shaped.get("selectiveLogic", 0)),
            ignore_budget=bool(shaped.get("ignoreBudget", False)),
        )
    return LoreEntry.from_dict(with_st_entry_defaults(shaped))


def create_lorebook(session: Session, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    name = str(body.get("name", "New lorebook")).strip() or "New lorebook"
    existing_ids = [book.id for book in session.list_lorebooks()]
    try:
        book = create_empty_lorebook(name=name, existing_ids=existing_ids)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    session.update_lorebook(book)
    return {
        "ok": True,
        "lorebook_id": book.id,
        "message": f"Created empty lorebook {book.id!r}.",
        "lorebook": _serialize_book_detail(book),
    }


def load_demo_lorebook(session: Session) -> dict[str, Any]:
    studio_root = Path(__file__).resolve().parent.parent
    demo_path = studio_root / "fixtures" / "lorebooks" / "campaign-rpg-engine-demo.lorebook.json"
    if not demo_path.is_file():
        return {"ok": False, "message": f"Demo lorebook not found at {demo_path}."}
    try:
        book = load_lorebook_from_path(demo_path)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    session.update_lorebook(book)
    return {
        "ok": True,
        "lorebook_id": book.id,
        "message": f"Loaded demo lorebook {book.id!r} ({len(book.entries)} entries).",
        "lorebook": _serialize_book_detail(book),
    }


def list_lorebooks(session: Session) -> dict[str, Any]:
    books = []
    for book in session.list_lorebooks():
        books.append(
            {
                "id": book.id,
                "name": book.name,
                "source_filename": book.source_filename,
                "entry_count": len(book.entries),
            }
        )
    return {"ok": True, "lorebooks": books}


def get_lorebook(session: Session, book_id: str) -> dict[str, Any]:
    book = session.get_lorebook(book_id)
    if book is None:
        return {"ok": False, "message": f"Lorebook {book_id!r} not found."}
    return {"ok": True, "lorebook": _serialize_book_detail(book)}


def put_lorebook(session: Session, book_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = session.get_lorebook(book_id)
    if existing is None:
        return {"ok": False, "message": f"Lorebook {book_id!r} not found."}
    entries_raw = payload.get("entries")
    if not isinstance(entries_raw, list):
        return {"ok": False, "message": "entries must be an array."}
    existing_by_uid = {entry.uid: entry for entry in existing.entries}
    entries: list[LoreEntry] = []
    for index, item in enumerate(entries_raw):
        if not isinstance(item, dict):
            return {"ok": False, "message": f"Entry {index + 1} must be an object."}
        uid = int(item.get("uid", 0))
        entries.append(_entry_from_payload(item, previous=existing_by_uid.get(uid)))
    name = str(payload.get("name", existing.name)).strip() or existing.name
    book = Lorebook(
        id=book_id,
        name=name,
        source_filename=existing.source_filename,
        entries=entries,
    )
    session.update_lorebook(book)
    return {"ok": True, "lorebook": _serialize_book_detail(book)}


def delete_lorebook(session: Session, book_id: str) -> dict[str, Any]:
    if not session.remove_lorebook(book_id):
        return {"ok": False, "message": f"Lorebook {book_id!r} not found."}
    return {"ok": True, "message": f"Removed lorebook {book_id!r}."}


def upload_lorebook(session: Session, *, source: str, filename: str) -> dict[str, Any]:
    try:
        data = json.loads(source)
    except json.JSONDecodeError as exc:
        return {"ok": False, "message": f"Invalid JSON: {exc}"}
    if not isinstance(data, dict):
        return {"ok": False, "message": "Lorebook JSON root must be an object."}
    try:
        book = load_lorebook_from_dict(data, filename=filename)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    session.update_lorebook(book)
    return {
        "ok": True,
        "lorebook_id": book.id,
        "message": f"Loaded lorebook {book.id!r} ({len(book.entries)} entries).",
        "lorebook": _serialize_book_detail(book),
    }


def export_lorebook_download(session: Session, book_id: str) -> dict[str, Any]:
    book = session.get_lorebook(book_id)
    if book is None:
        return {"ok": False, "message": f"Lorebook {book_id!r} not found."}
    return {
        "ok": True,
        "filename": book.export_filename(),
        "payload": book.to_st_export_dict(),
    }


def _serialize_book_detail(book: Lorebook) -> dict[str, Any]:
    return {
        "id": book.id,
        "name": book.name,
        "source_filename": book.source_filename,
        "entries": [
            {
                "uid": entry.uid,
                "enabled": entry.enabled,
                "constant": entry.constant,
                "keys": list(entry.keys),
                "keys_secondary": list(entry.keys_secondary),
                "selective": entry.selective,
                "selective_logic": entry.selective_logic,
                "content": entry.content,
                "comment": entry.comment,
                "order": entry.order,
                "ignore_budget": entry.ignore_budget,
            }
            for entry in book.sorted_entries()
        ],
    }
