"""sequence reference handler — run multiple handlers in order."""

from __future__ import annotations

from campaign_rpg_engine.action_outcome import ActionOutcome
from campaign_rpg_engine.interaction_handlers import (
    collect_prefixed_params,
    is_handler_registered,
    run_named_handler,
    validate_handler_params,
)

_MAX_STEPS = 20


def _iter_sequence_steps(params: dict[str, str]) -> list[tuple[str, dict[str, str]]]:
    steps: list[tuple[str, dict[str, str]]] = []
    for i in range(1, _MAX_STEPS + 1):
        key = f"handler_{i}"
        handler_id = (params.get(key) or "").strip()
        if not handler_id or handler_id == "none":
            break
        nested = collect_prefixed_params(params, f"{i}_", skip_keys={key})
        steps.append((handler_id, nested))
    return steps


def validate_sequence_params(params: dict[str, str]) -> str | None:
    steps = _iter_sequence_steps(params)
    if not steps:
        return "sequence requires handler_1 <handler_id>."
    for handler_id, nested in steps:
        if not is_handler_registered(handler_id):
            return f"Unknown sequence handler '{handler_id}'."
        if handler_id == "sequence":
            return "sequence cannot nest another sequence handler."
        err = validate_handler_params(handler_id, nested)
        if err:
            return err
    return None


def sequence(session, area, agent, obj, action) -> ActionOutcome | str | None:
    steps = _iter_sequence_steps(action.handler_params)
    if not steps:
        return "sequence requires handler_1 <handler_id>."
    for handler_id, nested in steps:
        out = run_named_handler(
            session,
            area,
            agent,
            obj,
            handler_id,
            nested,
            source_action=action,
        )
        if isinstance(out, str):
            return out
        if out is not None:
            return out
    return None
