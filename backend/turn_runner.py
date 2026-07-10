"""
Run compound turns for realm-studio (LLM or manual player input).
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from realm_fabric import (
    AgentCompoundTurn,
    LLMParseError,
    Session,
    TurnRecord,
    estimate_prompt_tokens,
    get_compound_turn,
)

from backend.snapshot_compat import normalize_state_snapshot


def _serialize_steps(record: TurnRecord) -> list[dict[str, Any]]:
    return [
        {
            "kind": step.kind,
            "result": step.result,
            "reasoning": step.reasoning,
            "target": step.target,
            "content": step.content,
        }
        for step in record.steps
    ]


def _resolve_agent(session: Session, agent_id: str | None):
    if agent_id is not None:
        return session.get_agent(agent_id)
    return session.get_active_agent()


def run_manual_turn(
    session: Session,
    turn_payload: dict[str, Any],
    *,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Validate manual compound JSON and run a player-agent turn (no LLM)."""
    if agent_id is not None and session.get_agent(agent_id) is None:
        return {"ok": False, "message": f"Agent {agent_id!r} not found."}

    agent = _resolve_agent(session, agent_id)
    if agent is None:
        return {"ok": False, "message": "No active agent."}
    if not agent.is_player:
        return {
            "ok": False,
            "message": "Manual turns are only available for player agents.",
        }

    gate = session.gate_agent_turn(agent_id)
    if not gate.ok:
        return {"ok": False, "message": gate.message}

    try:
        compound_turn = AgentCompoundTurn.model_validate(turn_payload)
    except ValidationError as exc:
        return {"ok": False, "message": str(exc)}

    result = session.run_compound_turn(compound_turn, agent_id=agent_id)
    if not result.ok or result.record is None:
        return {"ok": False, "message": result.message}

    return {
        "ok": True,
        "message": result.message,
        "snapshot": normalize_state_snapshot(
            session.snapshot(include_private=True)
        ),
        "steps": _serialize_steps(result.record),
        "manual_turn": True,
    }


def run_llm_turn(
    session: Session,
    *,
    agent_id: str | None = None,
    include_examples: bool | None = None,
) -> dict[str, Any]:
    """
    gate → build_prompt → LLM → run_compound_turn.

    Returns ``{ ok, message, snapshot?, steps? }`` for the HTTP handler.
    """
    prev_include = session.include_examples
    if include_examples is not None:
        session.include_examples = include_examples

    try:
        if agent_id is not None and session.get_agent(agent_id) is None:
            return {"ok": False, "message": f"Agent {agent_id!r} not found."}

        agent = _resolve_agent(session, agent_id)
        if agent is not None and agent.is_player:
            return {
                "ok": False,
                "message": (
                    f"{agent.name} is a player agent; use the manual turn form "
                    "(Run turn ▶)."
                ),
            }

        gate = session.gate_agent_turn(agent_id)
        if not gate.ok:
            return {"ok": False, "message": gate.message}

        try:
            prompt = session.build_prompt(agent_id)
            response = get_compound_turn(prompt)
            compound_turn = response.parsed
        except RuntimeError as exc:
            return {"ok": False, "message": str(exc)}
        except LLMParseError as exc:
            return {"ok": False, "message": str(exc)}

        result = session.run_compound_turn(compound_turn, agent_id=agent_id)
        if not result.ok or result.record is None:
            return {"ok": False, "message": result.message}

        return {
            "ok": True,
            "message": result.message,
            "snapshot": normalize_state_snapshot(
                session.snapshot(include_private=True)
            ),
            "steps": _serialize_steps(result.record),
            "prompt": prompt,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "prompt_tokens_estimate": estimate_prompt_tokens(prompt),
            "llm_response": response.raw_response,
        }
    finally:
        session.include_examples = prev_include
