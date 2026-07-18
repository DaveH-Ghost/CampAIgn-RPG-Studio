"""spawn_from_template reference handler — place a library object template in the world."""

from __future__ import annotations

from campaign_rpg_engine import parse_position


def validate_spawn_from_template_params(params: dict[str, str]) -> str | None:
    template_id = (params.get("template_id") or "").strip()
    if not template_id:
        return "spawn_from_template requires template_id."
    dest_at = (params.get("dest-at") or "").strip()
    if dest_at:
        _, err = parse_position(dest_at)
        if err:
            return err
    return None


def _candidate_positions(agent, area, preferred: tuple[int, int] | None):
    if preferred is not None:
        yield preferred
    ax, ay = agent.position
    yield (ax, ay)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            pos = (ax + dx, ay + dy)
            if area.is_valid_position(pos):
                yield pos


def spawn_from_template(session, area, agent, obj, action) -> str | None:
    del obj
    if session is None:
        return "spawn_from_template requires a session."

    from backend.entity_templates_api import get_entity_template
    from campaign_rpg_engine import spawn_object_from_template

    params = action.handler_params
    template_id = (params.get("template_id") or "").strip()
    loaded = get_entity_template(template_id)
    if not loaded.get("ok"):
        return str(loaded.get("message") or f"Template {template_id!r} not found.")
    template = loaded["template"]
    if not isinstance(template, dict) or template.get("kind") != "object":
        return f"Template {template_id!r} must be an object template."

    dest_area = (params.get("dest-area") or "").strip() or None
    dest_at_raw = (params.get("dest-at") or "").strip()
    preferred = None
    if dest_at_raw:
        preferred, err = parse_position(dest_at_raw)
        if err:
            return err

    spawn_area = area
    area_id = dest_area
    if dest_area:
        spawn_area = session.areas.get(dest_area)
        if spawn_area is None:
            return f"Unknown area {dest_area!r}."
    else:
        area_id = session.agent_area.get(agent.id) or session.active_area_id

    last_err = "No valid spawn position."
    for position in _candidate_positions(agent, spawn_area, preferred):
        result = spawn_object_from_template(
            session,
            template,
            position,
            area_id=area_id,
        )
        if result.ok:
            return None
        last_err = result.message or last_err
        if preferred is not None:
            # Explicit dest-at failed — don't wander to other tiles.
            return last_err
    return last_err
