"""Session change fan-out for Studio SSE streams (replace client polling)."""

from __future__ import annotations

import queue
import threading

_revision = 0
_lock = threading.Lock()
_subscribers: list[queue.Queue[int]] = []


def current_revision() -> int:
    with _lock:
        return _revision


def publish_session_changed() -> None:
    """Bump revision and wake all SSE subscribers."""
    global _revision
    with _lock:
        _revision += 1
        rev = _revision
        subscribers = list(_subscribers)
    for sub in subscribers:
        try:
            sub.put_nowait(rev)
        except queue.Full:
            try:
                sub.get_nowait()
            except queue.Empty:
                pass
            try:
                sub.put_nowait(rev)
            except queue.Full:
                pass


def subscribe() -> queue.Queue[int]:
    """Subscribe to revision updates. Queue is primed with the current revision."""
    sub: queue.Queue[int] = queue.Queue(maxsize=4)
    with _lock:
        _subscribers.append(sub)
        sub.put_nowait(_revision)
    return sub


def unsubscribe(sub: queue.Queue[int]) -> None:
    with _lock:
        if sub in _subscribers:
            _subscribers.remove(sub)


def wait_revision(sub: queue.Queue[int], timeout: float) -> int | None:
    """Block until a revision arrives, or return None on timeout (keepalive)."""
    try:
        return sub.get(timeout=timeout)
    except queue.Empty:
        return None


def reset_session_events_for_tests() -> None:
    """Clear subscribers and revision (tests only)."""
    global _revision
    with _lock:
        _revision = 0
        _subscribers.clear()
