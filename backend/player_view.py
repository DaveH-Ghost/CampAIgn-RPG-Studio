"""Build player-scoped session views for /api/player/* (Studio 1.7.0)."""

from __future__ import annotations

from typing import Any

from campaign_rpg_engine import Session, build_passive_vision
from campaign_rpg_engine.area_event import AREA_EVENT_ACTOR_ID
from campaign_rpg_engine.grid import chebyshev_distance
from campaign_rpg_engine.turn_record import TurnRecord

from backend.initiative import player_initiative_fields
from backend.plugin_registry import merged_player_turn_assist
from backend.snapshot_compat import normalize_state_snapshot

_SOCIAL_RANGE = 1
_PUBLIC_AGENT_KEYS = (
    "id",
    "name",
    "position",
    "appearance",
    "area_id",
    "is_player",
)
_PUBLIC_OBJECT_KEYS = (
    "id",
    "name",
    "position",
    "appearance",
    "width",
    "height",
    "actions",
    "actions_detail",
    "hidden",
)


def build_player_history(agent) -> list[dict[str, Any]]:
    """
    Chronological feed of this agent's own turns and witnessed passives.

    Own compound turns are one entry (all step results joined) for readability.
    Witnessed compound turns are also grouped: consecutive events with the same
    actor and session_turn (one broadcast per step) become a single card.
    Built from the agent's memory module buffers (recent/salient/rolling).
    """
    module = agent.memory.module
    turns: list[TurnRecord] = list(getattr(module, "_turns", None) or agent.memory.turns)
    witnessed_before = list(getattr(module, "_witnessed_before", []) or [])
    pending = list(getattr(module, "_pending", []) or [])

    entries: list[dict[str, Any]] = []
    for index, turn in enumerate(turns):
        before = witnessed_before[index] if index < len(witnessed_before) else []
        entries.extend(_grouped_witness_entries(before))
        lines: list[str] = []
        kinds: list[str] = []
        for step in turn.steps:
            text = (step.result or "").strip()
            if not text:
                continue
            lines.append(text)
            kinds.append(str(step.kind or "step"))
        if lines:
            entries.append(
                {
                    "source": "you",
                    "kind": kinds[0] if len(kinds) == 1 else "compound",
                    "kinds": kinds,
                    "turn": turn.turn_number,
                    "text": "\n".join(lines),
                }
            )

    entries.extend(_grouped_witness_entries(pending))
    return entries


def _witness_group_key(event) -> tuple[Any, ...]:
    """Group key for consecutive witnessed steps from one actor turn."""
    actor_id = getattr(event, "actor_id", "") or ""
    session_turn = getattr(event, "session_turn", None)
    return (actor_id, session_turn)


def _grouped_witness_entries(events: list[Any]) -> list[dict[str, Any]]:
    """Collapse consecutive same-actor/session_turn witness events into one entry."""
    if not events:
        return []
    grouped: list[dict[str, Any]] = []
    batch: list[Any] = []
    for event in events:
        if batch and _witness_group_key(event) != _witness_group_key(batch[0]):
            grouped.append(_witness_entry_from_batch(batch))
            batch = []
        batch.append(event)
    if batch:
        grouped.append(_witness_entry_from_batch(batch))
    return grouped


def _witness_entry_from_batch(events: list[Any]) -> dict[str, Any]:
    lines = [
        text
        for text in ((getattr(e, "text", None) or "").strip() for e in events)
        if text
    ]
    first = events[0]
    actor_id = getattr(first, "actor_id", "") or ""
    if actor_id == AREA_EVENT_ACTOR_ID:
        source = "event"
        actor_name = ""
    else:
        source = "witness"
        actor_name = getattr(first, "actor_name", "") or ""
    return {
        "source": source,
        "kind": "compound" if len(lines) > 1 else "observe",
        "turn": getattr(first, "session_turn", None),
        "actor_id": actor_id,
        "actor_name": actor_name,
        "text": "\n".join(lines),
    }


def build_player_view(session: Session, agent_id: str) -> dict[str, Any]:
    """Filtered snapshot for one seated player agent (their area only)."""
    agent = session.get_agent(agent_id)
    if agent is None:
        raise KeyError(agent_id)
    if not agent.is_player:
        raise ValueError(f"Agent {agent_id!r} is not a player agent.")

    area_id = session.agent_area.get(agent.id)
    if not area_id or area_id not in session.areas:
        raise ValueError(f"Agent {agent_id!r} has no area.")

    area = session.areas[area_id]
    prev_active = session.active_agent_id
    try:
        session.active_agent_id = agent.id
        full = normalize_state_snapshot(session.snapshot(include_private=False))
        passive = build_passive_vision(agent, area)
        assist = _assist_for_agent(session, agent.id)
    finally:
        session.active_agent_id = prev_active

    area_block = (full.get("areas") or {}).get(area_id) or {}
    objects = [
        _public_object(obj)
        for obj in (area_block.get("objects") or [])
        if isinstance(obj, dict) and not obj.get("hidden")
    ]
    agents = [
        _public_agent(a)
        for a in (full.get("agents") or [])
        if isinstance(a, dict) and (a.get("area_id") or full.get("active_area_id")) == area_id
    ]

    social_candidates = []
    ax, ay = agent.position
    for other in agents:
        if other["id"] == agent.id:
            continue
        pos = other.get("position") or [0, 0]
        try:
            ox, oy = int(pos[0]), int(pos[1])
        except (TypeError, ValueError, IndexError):
            continue
        if chebyshev_distance((ax, ay), (ox, oy)) <= _SOCIAL_RANGE:
            social_candidates.append({"id": other["id"], "name": other["name"]})

    return {
        "ok": True,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "area_id": area_id,
        "session_turn": full.get("session_turn"),
        "coordinate_mode": full.get("coordinate_mode"),
        "vision_units": full.get("vision_units"),
        "vision_units_per_tile": full.get("vision_units_per_tile"),
        "passive_vision": passive,
        "grid": area_block.get("grid"),
        "area_description": area_block.get("area_description") or "",
        "decorations": list(area_block.get("decorations") or []),
        "objects": objects,
        "agents": agents,
        "recent_events": list(area_block.get("recent_events") or []),
        "history": build_player_history(agent),
        "assist": assist,
        "social_candidates": social_candidates,
        **player_initiative_fields(session, agent.id),
    }


def _assist_for_agent(session: Session, agent_id: str) -> list[dict[str, Any]]:
    """Inventory/assist rows for *agent_id*, with give/show on inventory items."""
    prev = session.active_agent_id
    try:
        session.active_agent_id = agent_id
        rows = merged_player_turn_assist(session)
    finally:
        session.active_agent_id = prev

    enriched: list[dict[str, Any]] = []
    for row in rows:
        verbs = list(row.get("verbs") or [])
        if row.get("plugin_id") == "inventory":
            for extra in ("give", "show"):
                if extra not in verbs:
                    verbs.append(extra)
        enriched.append({**row, "verbs": verbs})
    return enriched


def _public_agent(agent: dict[str, Any]) -> dict[str, Any]:
    return {k: agent.get(k) for k in _PUBLIC_AGENT_KEYS if k in agent}


def _public_object(obj: dict[str, Any]) -> dict[str, Any]:
    out = {k: obj.get(k) for k in _PUBLIC_OBJECT_KEYS if k in obj}
    # Player client should not see hidden; strip the flag if present.
    out.pop("hidden", None)
    return out
