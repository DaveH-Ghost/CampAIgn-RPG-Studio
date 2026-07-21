"""
Run compound turns for campaign-rpg-studio (LLM or manual player input).
"""

from __future__ import annotations

from typing import Any

from campaign_rpg_engine import (
    AgentCompoundTurn,
    ConcurrencyLimitError,
    LLMParseError,
    PromptTooLargeError,
    Session,
    TurnRecord,
    estimate_prompt_tokens,
    get_compound_turn,
    is_concurrency_limit_error,
    prompt_token_budget_status,
)
from pydantic import ValidationError

from backend.initiative import (
    can_agent_act,
    initiative_enabled,
    maybe_advance_after_turn,
    sync_active_agent,
)
from backend.session_store import get_session_store
from backend.snapshot_compat import normalize_state_snapshot

ERROR_CODE_CONCURRENCY_LIMIT = "concurrency_limit_exceeded"


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


def _active_agent_before_explicit_turn(session: Session, agent_id: str | None) -> str | None:
    """When *agent_id* is set, remember POV agent so we can restore after the turn."""
    if agent_id is None:
        return None
    return session.active_agent_id


def _restore_active_agent(session: Session, previous_active_id: str | None) -> None:
    if previous_active_id is not None:
        session.active_agent_id = previous_active_id


def _undo_fields() -> dict[str, Any]:
    store = get_session_store()
    return {
        "can_undo": store.can_undo,
        "undo_remaining": store.undo_remaining,
    }


def _concurrency_fields(error_code: str | None = None, *, flag: bool = False) -> dict[str, Any]:
    exceeded = flag or error_code == ERROR_CODE_CONCURRENCY_LIMIT
    if not exceeded:
        return {}
    return {
        "error_code": ERROR_CODE_CONCURRENCY_LIMIT,
        "concurrency_limit_exceeded": True,
    }


def _failure(message: str, *, error_code: str | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": False, "message": message, **extra}
    payload.update(_concurrency_fields(error_code))
    return payload


def run_manual_turn(
    session: Session,
    turn_payload: dict[str, Any],
    *,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Validate manual compound JSON and run a player-agent turn (no LLM)."""
    if agent_id is not None and session.get_agent(agent_id) is None:
        return _failure(f"Agent {agent_id!r} not found.")

    agent = _resolve_agent(session, agent_id)
    if agent is None:
        return _failure("No active agent.")
    if not agent.is_player:
        return _failure("Manual turns are only available for player agents.")

    gate = can_agent_act(session, agent.id)
    if not gate.ok:
        return _failure(gate.message, error_code=gate.error_code)

    try:
        compound_turn = AgentCompoundTurn.model_validate(turn_payload)
    except ValidationError as exc:
        return _failure(str(exc))

    store = get_session_store()
    checkpoint = store.capture_checkpoint()
    prev_active = _active_agent_before_explicit_turn(session, agent_id)
    acting_id = agent.id
    result = session.run_compound_turn(compound_turn, agent_id=agent_id)
    if not result.ok or result.record is None:
        _restore_active_agent(session, prev_active)
        return _failure(result.message, error_code=getattr(result, "error_code", None))

    if initiative_enabled(session):
        maybe_advance_after_turn(session, acting_id)
        sync_active_agent(session)
    else:
        _restore_active_agent(session, prev_active)

    store.push_undo(checkpoint)
    return {
        "ok": True,
        "message": result.message,
        "snapshot": normalize_state_snapshot(session.snapshot(include_private=True)),
        "steps": _serialize_steps(result.record),
        "manual_turn": True,
        **_undo_fields(),
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
            return _failure(f"Agent {agent_id!r} not found.")

        agent = _resolve_agent(session, agent_id)
        if agent is not None and agent.is_player:
            return _failure(
                f"{agent.name} is a player agent; use the manual turn form (Run turn ▶)."
            )

        gate = can_agent_act(session, agent.id)
        if not gate.ok:
            return _failure(gate.message, error_code=gate.error_code)

        prompt = None
        try:
            prompt = session.build_prompt(agent_id)
            response = get_compound_turn(prompt)
            compound_turn = response.parsed
        except PromptTooLargeError as exc:
            budget = prompt_token_budget_status(prompt or "")
            return {
                "ok": False,
                "message": str(exc),
                "prompt": prompt,
                "prompt_tokens_estimate": exc.estimate,
                "max_input_tokens": exc.limit,
                "over_limit": True,
                "over_warning": budget["over_warning"],
                "warning_threshold": budget["warning_threshold"],
            }
        except ConcurrencyLimitError as exc:
            return _failure(str(exc), error_code=ConcurrencyLimitError.ERROR_CODE, prompt=prompt)
        except RuntimeError as exc:
            if is_concurrency_limit_error(exc):
                return _failure(
                    str(exc),
                    error_code=ERROR_CODE_CONCURRENCY_LIMIT,
                    prompt=prompt,
                )
            return _failure(str(exc), prompt=prompt)
        except LLMParseError as exc:
            payload: dict = {
                "ok": False,
                "message": str(exc),
                "prompt": prompt,
            }
            if exc.raw_response:
                payload["llm_response"] = exc.raw_response
            if prompt:
                payload["prompt_tokens_estimate"] = estimate_prompt_tokens(prompt)
            return payload
        except Exception as exc:
            if is_concurrency_limit_error(exc):
                return _failure(
                    str(exc),
                    error_code=ERROR_CODE_CONCURRENCY_LIMIT,
                    prompt=prompt,
                )
            raise

        store = get_session_store()
        checkpoint = store.capture_checkpoint()
        prev_active = _active_agent_before_explicit_turn(session, agent_id)
        acting_id = agent.id
        result = session.run_compound_turn(compound_turn, agent_id=agent_id)
        if not result.ok or result.record is None:
            _restore_active_agent(session, prev_active)
            return _failure(result.message, error_code=getattr(result, "error_code", None))

        if initiative_enabled(session):
            maybe_advance_after_turn(session, acting_id)
            sync_active_agent(session)
        else:
            _restore_active_agent(session, prev_active)

        store.push_undo(checkpoint)
        return {
            "ok": True,
            "message": result.message,
            "snapshot": normalize_state_snapshot(session.snapshot(include_private=True)),
            "steps": _serialize_steps(result.record),
            "prompt": prompt,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "prompt_tokens_estimate": estimate_prompt_tokens(prompt),
            "llm_response": response.raw_response,
            **_undo_fields(),
        }
    finally:
        session.include_examples = prev_include
