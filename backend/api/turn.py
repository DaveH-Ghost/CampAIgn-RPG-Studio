"""Turn routes: LLM turn, manual player turn, undo."""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import ManualTurnRequest, TurnRequest
from backend.session_store import get_session_store
from backend.turn_runner import run_llm_turn, run_manual_turn

router = APIRouter()


@router.post("/api/turn")
def post_turn(body: TurnRequest) -> dict[str, object]:
    return run_llm_turn(
        get_session_store().session,
        agent_id=body.agent_id,
        include_examples=body.include_examples,
    )


@router.post("/api/turn/manual")
def post_manual_turn(body: ManualTurnRequest) -> dict[str, object]:
    return run_manual_turn(
        get_session_store().session,
        body.compound_turn,
        agent_id=body.agent_id,
    )


@router.get("/api/turn/undo")
def get_turn_undo_status() -> dict[str, object]:
    return get_session_store().undo_status()


@router.post("/api/turn/undo")
def post_turn_undo() -> dict[str, object]:
    return get_session_store().undo_turn()
