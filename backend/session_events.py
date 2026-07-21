"""Session change fan-out for Studio SSE streams (replace client polling)."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Any

_revision = 0
_lock = threading.Lock()
_subscribers: list[queue.Queue["SessionPush"]] = []


@dataclass(frozen=True)
class SessionPush:
    """One SSE wake-up: session mutation or a typed alert."""

    revision: int
    event: str = "change"
    data: dict[str, Any] = field(default_factory=dict)


def current_revision() -> int:
    with _lock:
        return _revision


def _publish(event: str, data: dict[str, Any] | None = None) -> SessionPush:
    global _revision
    with _lock:
        _revision += 1
        push = SessionPush(revision=_revision, event=event, data=dict(data or {}))
        subscribers = list(_subscribers)
    for sub in subscribers:
        try:
            sub.put_nowait(push)
        except queue.Full:
            try:
                sub.get_nowait()
            except queue.Empty:
                pass
            try:
                sub.put_nowait(push)
            except queue.Full:
                pass
    return push


def publish_session_changed() -> None:
    """Bump revision and wake all SSE subscribers (generic session mutation)."""
    _publish("change")


def publish_concurrency_limit(
    *,
    message: str = "",
    agent_name: str = "",
    turn_number: int | None = None,
) -> None:
    """Push a concurrency-limit alert to GM SSE clients immediately."""
    _publish(
        "concurrency_limit",
        {
            "concurrency_limit_exceeded": True,
            "error_code": "concurrency_limit_exceeded",
            "message": message
            or (
                "LLM concurrency limit exceeded during memory consolidation "
                "(or affinity Call A/B)."
            ),
            "agent_name": agent_name,
            "turn_number": turn_number,
        },
    )


def subscribe() -> queue.Queue[SessionPush]:
    """Subscribe to push updates. Queue is primed with the current revision."""
    sub: queue.Queue[SessionPush] = queue.Queue(maxsize=8)
    with _lock:
        _subscribers.append(sub)
        sub.put_nowait(SessionPush(revision=_revision, event="change"))
    return sub


def unsubscribe(sub: queue.Queue[SessionPush]) -> None:
    with _lock:
        if sub in _subscribers:
            _subscribers.remove(sub)


def wait_push(sub: queue.Queue[SessionPush], timeout: float) -> SessionPush | None:
    """Block until a push arrives, or return None on timeout (keepalive)."""
    try:
        return sub.get(timeout=timeout)
    except queue.Empty:
        return None


def wait_revision(sub: queue.Queue[SessionPush], timeout: float) -> int | None:
    """Back-compat: return revision int or None on timeout."""
    push = wait_push(sub, timeout)
    return None if push is None else push.revision


def reset_session_events_for_tests() -> None:
    """Clear subscribers and revision (tests only)."""
    global _revision
    with _lock:
        _revision = 0
        _subscribers.clear()
