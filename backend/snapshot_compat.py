"""Normalize session snapshots for campaign-rpg-studio clients (V0.4.0c1–c2)."""

from __future__ import annotations

from typing import Any

from backend.initiative import attach_initiative_to_snapshot

DEFAULT_AREA_ID = "room"


def normalize_state_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    """
    Return a complete multi-area snapshot for the campaign-rpg-studio UI.

    Upgrades legacy flat snapshots and guarantees each area block has list
    ``objects`` / ``recent_events`` fields.
    """
    if data.get("areas"):
        return _ensure_area_arrays(data)

    grid = data.get("grid")
    if not grid:
        return _ensure_area_arrays(
            {
                **data,
                "active_area_id": data.get("active_area_id") or DEFAULT_AREA_ID,
                "areas": {},
                "agents": data.get("agents") or [],
            }
        )

    area_id = data.get("active_area_id") or DEFAULT_AREA_ID
    return _ensure_area_arrays(
        {
            **data,
            "active_area_id": area_id,
            "areas": {
                area_id: {
                    "grid": grid,
                    "area_description": data.get("area_description", ""),
                    "objects": data.get("objects") or [],
                    "recent_events": data.get("recent_events") or [],
                },
            },
            "agents": [
                {**agent, "area_id": agent.get("area_id") or area_id}
                for agent in (data.get("agents") or [])
            ],
        }
    )


def _ensure_area_arrays(data: dict[str, Any]) -> dict[str, Any]:
    areas = data.get("areas") or {}
    fixed_areas: dict[str, Any] = {}
    for area_id, area in areas.items():
        block = dict(area) if isinstance(area, dict) else {}
        if not isinstance(block.get("objects"), list):
            block["objects"] = []
        if not isinstance(block.get("decorations"), list):
            block["decorations"] = []
        if not isinstance(block.get("recent_events"), list):
            block["recent_events"] = []
        fixed_areas[area_id] = block

    active_area_id = data.get("active_area_id") or DEFAULT_AREA_ID
    agents = [
        {**agent, "area_id": agent.get("area_id") or active_area_id}
        for agent in (data.get("agents") or [])
        if isinstance(agent, dict)
    ]

    result = {
        **data,
        "active_area_id": active_area_id,
        "areas": fixed_areas,
        "agents": agents,
    }
    for key in ("grid", "area_description", "objects", "recent_events"):
        result.pop(key, None)
    return attach_initiative_to_snapshot(result)


def flatten_snapshot_for_ui(data: dict[str, Any]) -> dict[str, Any]:
    """Legacy flat view (tests / migration). Prefer ``normalize_state_snapshot``."""
    normalized = normalize_state_snapshot(data)
    if not normalized.get("areas"):
        return normalized

    area_id = normalized.get("active_area_id") or DEFAULT_AREA_ID
    block = normalized["areas"].get(area_id) or {}
    agents = [
        agent
        for agent in normalized.get("agents") or []
        if agent.get("area_id", area_id) == area_id
    ]
    result: dict[str, Any] = {
        "grid": block.get("grid"),
        "area_description": block.get("area_description", ""),
        "objects": block.get("objects") or [],
        "recent_events": block.get("recent_events") or [],
        "session_turn": normalized.get("session_turn", 0),
        "active_agent_id": normalized.get("active_agent_id"),
        "agents": agents,
    }
    if "passive_vision" in normalized:
        result["passive_vision"] = normalized["passive_vision"]
    return result
