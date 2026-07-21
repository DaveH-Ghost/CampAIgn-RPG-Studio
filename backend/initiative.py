"""Initiative turn order for campaign-rpg-studio (1.7.1).

Stored in ``session.extensions["initiative"]``; exposed on GM snapshots as top-level
``initiative`` via ``snapshot_compat``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from campaign_rpg_engine import Session

INITIATIVE_KEY = "initiative"
WAIT_REASON = "It is not your turn."


@dataclass(frozen=True)
class InitiativeGate:
    ok: bool
    message: str = ""
    error_code: str | None = None


def _default_state() -> dict[str, Any]:
    return {"enabled": False, "order": [], "index": 0, "round": 1}


def _ensure_state(session: Session) -> dict[str, Any]:
    raw = session.get_extension(INITIATIVE_KEY)
    if not isinstance(raw, dict):
        raw = _default_state()
        session.set_extension(INITIATIVE_KEY, raw)
    if not isinstance(raw.get("order"), list):
        raw["order"] = []
    if not isinstance(raw.get("index"), int):
        raw["index"] = 0
    if not isinstance(raw.get("round"), int):
        raw["round"] = 1
    raw["enabled"] = bool(raw.get("enabled"))
    return raw


def _valid_agent_ids(session: Session) -> set[str]:
    ids: set[str] = set()
    for area in session.areas.values():
        for agent in area.agents:
            ids.add(agent.id)
    return ids


def _prune_order(session: Session, order: list[Any]) -> list[str]:
    valid = _valid_agent_ids(session)
    return [str(aid) for aid in order if str(aid) in valid]


def get_initiative_state(session: Session) -> dict[str, Any]:
    """Return a copy of initiative state with pruned order."""
    raw = _ensure_state(session)
    order = _prune_order(session, raw.get("order") or [])
    if order != raw.get("order"):
        raw["order"] = order
        session.set_extension(INITIATIVE_KEY, raw)
    index = int(raw.get("index") or 0)
    if order and index >= len(order):
        raw["index"] = index % len(order)
    if raw.get("enabled") and not order:
        raw["enabled"] = False
    return dict(raw)


def initiative_enabled(session: Session) -> bool:
    return bool(get_initiative_state(session).get("enabled"))


def current_actor_id(session: Session) -> str | None:
    state = get_initiative_state(session)
    if not state.get("enabled"):
        return None
    order = state.get("order") or []
    if not order:
        return None
    index = int(state.get("index") or 0) % len(order)
    return order[index]


def _agent_name(session: Session, agent_id: str) -> str:
    agent = session.get_agent(agent_id)
    return agent.name if agent is not None else agent_id


def can_agent_act(session: Session, agent_id: str) -> InitiativeGate:
    gate = session.gate_agent_turn(agent_id)
    if not gate.ok:
        return InitiativeGate(
            False,
            gate.message,
            error_code=getattr(gate, "error_code", None),
        )
    if not initiative_enabled(session):
        return InitiativeGate(True)
    current = current_actor_id(session)
    if current is None:
        return InitiativeGate(True)
    if agent_id != current:
        current_name = _agent_name(session, current)
        return InitiativeGate(False, f"{WAIT_REASON} ({current_name}'s turn.)")
    return InitiativeGate(True)


def sync_active_agent(session: Session) -> None:
    """Point session active agent at the current initiative slot when enabled."""
    if not initiative_enabled(session):
        return
    current = current_actor_id(session)
    if current is None:
        return
    session.active_agent_id = current


def advance(session: Session) -> dict[str, Any]:
    """Advance to the next initiative slot; increment round on wrap."""
    state = get_initiative_state(session)
    order = state.get("order") or []
    if not order:
        return state
    index = int(state.get("index") or 0)
    next_index = (index + 1) % len(order)
    state["index"] = next_index
    if next_index == 0:
        state["round"] = int(state.get("round") or 1) + 1
    session.set_extension(INITIATIVE_KEY, state)
    sync_active_agent(session)
    return get_initiative_state(session)


def maybe_advance_after_turn(session: Session, acting_agent_id: str) -> None:
    """After a successful turn, advance if the actor matched the current slot."""
    if not initiative_enabled(session):
        return
    current = current_actor_id(session)
    if current is None or acting_agent_id != current:
        return
    advance(session)


def set_order(session: Session, order: list[str]) -> dict[str, Any]:
    state = get_initiative_state(session)
    pruned = _prune_order(session, order)
    state["order"] = pruned
    index = int(state.get("index") or 0)
    if pruned:
        state["index"] = min(index, len(pruned) - 1)
    else:
        state["index"] = 0
        state["enabled"] = False
    session.set_extension(INITIATIVE_KEY, state)
    if state.get("enabled"):
        sync_active_agent(session)
    return get_initiative_state(session)


def put_initiative(
    session: Session,
    *,
    enabled: bool | None = None,
    order: list[str] | None = None,
    index: int | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Update initiative; return (state, error_message)."""
    state = get_initiative_state(session)
    if order is not None:
        state["order"] = _prune_order(session, order)
    if index is not None:
        order_list = state.get("order") or []
        if order_list:
            state["index"] = max(0, min(int(index), len(order_list) - 1))
        else:
            state["index"] = 0
    if enabled is not None:
        if enabled and not (state.get("order") or []):
            return state, "Initiative order must not be empty when enabling."
        state["enabled"] = enabled
        if enabled:
            state["index"] = int(state.get("index") or 0)
            if state["index"] >= len(state["order"]):
                state["index"] = 0
    session.set_extension(INITIATIVE_KEY, state)
    if state.get("enabled"):
        sync_active_agent(session)
    return get_initiative_state(session), None


def advance_next(session: Session) -> dict[str, Any]:
    """GM manual advance without resolving a turn."""
    if not initiative_enabled(session):
        return get_initiative_state(session)
    return advance(session)


def public_initiative_from_session(session: Session) -> dict[str, Any]:
    """Build the GM-facing initiative block."""
    state = get_initiative_state(session)
    order = state.get("order") or []
    entries = []
    current = current_actor_id(session) if state.get("enabled") else None
    for aid in order:
        agent = session.get_agent(aid)
        entries.append(
            {
                "agent_id": aid,
                "agent_name": agent.name if agent is not None else aid,
                "is_player": bool(agent.is_player) if agent is not None else False,
                "is_current": aid == current,
            }
        )
    return {
        "enabled": bool(state.get("enabled")),
        "order": list(order),
        "index": int(state.get("index") or 0),
        "round": int(state.get("round") or 1),
        "current_agent_id": current,
        "entries": entries,
    }


def player_initiative_fields(session: Session, agent_id: str) -> dict[str, Any]:
    """Fields for ``build_player_view``."""
    gate = can_agent_act(session, agent_id)
    state = get_initiative_state(session)
    current_id = current_actor_id(session) if state.get("enabled") else None
    current_name = _agent_name(session, current_id) if current_id else None
    order_names = []
    if state.get("enabled"):
        for aid in state.get("order") or []:
            order_names.append({"agent_id": aid, "agent_name": _agent_name(session, aid)})
    return {
        "can_act": gate.ok,
        "wait_reason": None if gate.ok else gate.message,
        "initiative_enabled": bool(state.get("enabled")),
        "initiative_round": int(state.get("round") or 1) if state.get("enabled") else None,
        "initiative_current": (
            {"agent_id": current_id, "agent_name": current_name} if current_id else None
        ),
        "initiative_order": order_names if state.get("enabled") else [],
    }


def attach_initiative_to_snapshot(data: dict[str, Any], session: Session | None = None) -> dict[str, Any]:
    """Add top-level ``initiative`` for GM clients."""
    if session is not None:
        data["initiative"] = public_initiative_from_session(session)
        return data
    ext = data.get("extensions") if isinstance(data.get("extensions"), dict) else {}
    raw = ext.get(INITIATIVE_KEY) if isinstance(ext, dict) else None
    if not isinstance(raw, dict):
        data["initiative"] = {
            "enabled": False,
            "order": [],
            "index": 0,
            "round": 1,
            "current_agent_id": None,
            "entries": [],
        }
        return data
    order = [str(x) for x in (raw.get("order") or [])]
    enabled = bool(raw.get("enabled"))
    index = int(raw.get("index") or 0)
    current = order[index % len(order)] if enabled and order else None
    agents = {a.get("id"): a for a in (data.get("agents") or []) if isinstance(a, dict)}
    entries = []
    for aid in order:
        agent = agents.get(aid) or {}
        entries.append(
            {
                "agent_id": aid,
                "agent_name": agent.get("name") or aid,
                "is_player": bool(agent.get("is_player")),
                "is_current": aid == current,
            }
        )
    data["initiative"] = {
        "enabled": enabled,
        "order": order,
        "index": index,
        "round": int(raw.get("round") or 1),
        "current_agent_id": current,
        "entries": entries,
    }
    return data
