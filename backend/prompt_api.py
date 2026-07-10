"""Prompt block API helpers for realm-studio (V0.4.1b)."""

from __future__ import annotations

from realm_fabric import (
    Session,
    default_prompt_blocks,
    enrich_blocks_with_previews,
    prompt_block_catalog,
    prompt_blocks_from_dicts,
    prompt_slot_catalog,
)


def _resolve_prompt_agent_area(session: Session, agent_id: str | None = None):
    if agent_id is not None:
        agent = session.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id!r} not found.")
    else:
        agent = session.get_active_agent()
    area = session.get_area_for_agent(agent)
    return agent, area


def _blocks_payload(session: Session, blocks, *, agent_id: str | None = None) -> dict[str, object]:
    agent, area = _resolve_prompt_agent_area(session, agent_id)
    ctx = session.build_prompt_context_for_agent(agent_id)
    return {
        "ok": True,
        "blocks": enrich_blocks_with_previews(
            blocks,
            ctx,
            agent=agent,
            area=area,
            vision_units=session.vision_units,
            units_per_tile=session.vision_units_per_tile,
            lorebooks=session._lorebooks,
            lorebook_char_budget=session.lorebook_char_budget,
            lorebook_scan_config=session.lorebook_scan_config,
            passive_vision=ctx.passive_vision,
        ),
        "uses_default": session.prompt_blocks_use_default(),
    }


def get_prompt_blocks(session: Session, *, agent_id: str | None = None) -> dict[str, object]:
    blocks = session.get_prompt_blocks()
    payload = _blocks_payload(session, blocks, agent_id=agent_id)
    payload["uses_default"] = session.prompt_blocks_use_default()
    return payload


def put_prompt_blocks(session: Session, items: list[dict[str, object]]) -> dict[str, object]:
    blocks, err = prompt_blocks_from_dicts(items)
    if err:
        return {"ok": False, "message": err}
    set_err = session.set_prompt_blocks(blocks)
    if set_err:
        return {"ok": False, "message": set_err}
    return get_prompt_blocks(session)


def reset_prompt_blocks(session: Session) -> dict[str, object]:
    session.reset_prompt_blocks()
    return get_prompt_blocks(session)


def preview_prompt_blocks(
    session: Session,
    items: list[dict[str, object]],
    *,
    agent_id: str | None = None,
) -> dict[str, object]:
    try:
        agent, area = _resolve_prompt_agent_area(session, agent_id)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    blocks, err = prompt_blocks_from_dicts(items)
    if err:
        return {"ok": False, "message": err}
    ctx = session.build_prompt_context_for_agent(agent_id)
    return {
        "ok": True,
        "blocks": enrich_blocks_with_previews(
            blocks,
            ctx,
            agent=agent,
            area=area,
            vision_units=session.vision_units,
            units_per_tile=session.vision_units_per_tile,
            lorebooks=session._lorebooks,
            lorebook_char_budget=session.lorebook_char_budget,
            lorebook_scan_config=session.lorebook_scan_config,
            passive_vision=ctx.passive_vision,
        ),
    }


def get_prompt_slots(session: Session, agent_id: str | None = None) -> dict[str, object]:
    if agent_id is not None and session.get_agent(agent_id) is None:
        return {"ok": False, "message": f"Agent {agent_id!r} not found."}
    ctx = session.build_prompt_context_for_agent(agent_id)
    return {
        "ok": True,
        "slots": prompt_slot_catalog(ctx),
        "editable_sections": sorted({"compound_rules", "output_format"}),
        "default_block_count": len(default_prompt_blocks()),
    }


def get_prompt_block_catalog_route() -> dict[str, object]:
    return {"ok": True, **prompt_block_catalog()}
