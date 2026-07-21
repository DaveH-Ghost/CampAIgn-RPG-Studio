"""Bridge Engine consolidation failures into Studio SSE alerts."""

from __future__ import annotations

from campaign_rpg_engine.memory_modules.consolidation_hooks import (
    register_consolidation_failure_listener,
)

from backend.session_events import publish_concurrency_limit

_registered = False


def _on_consolidation_failure(
    *,
    agent_name: str = "",
    turn_number: int | None = None,
    concurrency_limit_exceeded: bool = False,
    message: str = "",
    **_extra,
) -> None:
    if not concurrency_limit_exceeded:
        return
    publish_concurrency_limit(
        message=message,
        agent_name=agent_name or "",
        turn_number=turn_number,
    )


def register_concurrency_limit_bridge() -> None:
    """Idempotent: wire consolidation concurrency failures to GM SSE."""
    global _registered
    if _registered:
        return
    register_consolidation_failure_listener(_on_consolidation_failure)
    _registered = True
