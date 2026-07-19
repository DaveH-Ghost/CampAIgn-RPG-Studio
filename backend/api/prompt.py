"""Prompt routes: prompt text, prompt blocks, slots, block catalog."""

from __future__ import annotations

from campaign_rpg_engine import prompt_token_budget_status
from fastapi import APIRouter

from backend.prompt_api import (
    get_prompt_block_catalog_route as api_get_prompt_block_catalog,
)
from backend.prompt_api import (
    get_prompt_blocks as api_get_prompt_blocks,
)
from backend.prompt_api import (
    get_prompt_slots as api_get_prompt_slots,
)
from backend.prompt_api import (
    preview_prompt_blocks as api_preview_prompt_blocks,
)
from backend.prompt_api import (
    put_prompt_blocks as api_put_prompt_blocks,
)
from backend.prompt_api import (
    reset_prompt_blocks as api_reset_prompt_blocks,
)
from backend.schemas import PromptBlocksPreviewRequest, PromptBlocksRequest
from backend.session_store import get_session_store

router = APIRouter()


@router.get("/api/prompt")
def get_prompt(agent_id: str | None = None) -> dict[str, object]:
    session = get_session_store().session
    if agent_id is not None and session.get_agent(agent_id) is None:
        return {"ok": False, "message": f"Agent {agent_id!r} not found."}
    prompt = session.build_prompt(agent_id)
    budget = prompt_token_budget_status(prompt)
    return {
        "ok": True,
        "prompt": prompt,
        "length": len(prompt),
        "prompt_tokens": budget["estimate"],
        "max_input_tokens": budget["limit"],
        "input_warning_percent": budget["warning_percent"],
        "warning_threshold": budget["warning_threshold"],
        "over_warning": budget["over_warning"],
        "over_limit": budget["over_limit"],
        "include_examples": session.include_examples,
    }


@router.get("/api/prompt-blocks")
def get_prompt_blocks_route(agent_id: str | None = None) -> dict[str, object]:
    return api_get_prompt_blocks(get_session_store().session, agent_id=agent_id)


@router.put("/api/prompt-blocks")
def put_prompt_blocks_route(body: PromptBlocksRequest) -> dict[str, object]:
    items = [block.model_dump() for block in body.blocks]
    return api_put_prompt_blocks(get_session_store().session, items)


@router.post("/api/prompt-blocks/preview")
def preview_prompt_blocks_route(body: PromptBlocksPreviewRequest) -> dict[str, object]:
    items = [block.model_dump() for block in body.blocks]
    return api_preview_prompt_blocks(
        get_session_store().session,
        items,
        agent_id=body.agent_id,
    )


@router.post("/api/prompt-blocks/reset")
def reset_prompt_blocks_route() -> dict[str, object]:
    return api_reset_prompt_blocks(get_session_store().session)


@router.get("/api/prompt-slots")
def get_prompt_slots_route(agent_id: str | None = None) -> dict[str, object]:
    return api_get_prompt_slots(get_session_store().session, agent_id)


@router.get("/api/prompt-block-catalog")
def get_prompt_block_catalog_route() -> dict[str, object]:
    return api_get_prompt_block_catalog(get_session_store().session)
