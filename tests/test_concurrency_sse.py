"""SSE concurrency-limit alerts from consolidation failures."""

from __future__ import annotations

from backend.concurrency_bridge import register_concurrency_limit_bridge
from backend.session_events import (
    reset_session_events_for_tests,
    subscribe,
    unsubscribe,
    wait_push,
)
from campaign_rpg_engine.memory_modules.consolidation_hooks import (
    clear_consolidation_failure_listeners_for_tests,
    notify_consolidation_failure,
)


def setup_function():
    reset_session_events_for_tests()
    clear_consolidation_failure_listeners_for_tests()
    # Force re-register for this process (bridge is normally idempotent).
    import backend.concurrency_bridge as bridge

    bridge._registered = False
    register_concurrency_limit_bridge()


def teardown_function():
    reset_session_events_for_tests()
    clear_consolidation_failure_listeners_for_tests()
    import backend.concurrency_bridge as bridge

    bridge._registered = False


def test_concurrency_failure_publishes_sse_push():
    sub = subscribe()
    try:
        # Drain the primed change push.
        wait_push(sub, 0.05)

        notify_consolidation_failure(
            agent_name="Praxis",
            turn_number=3,
            concurrency_limit_exceeded=True,
            message="Concurrency limit exceeded",
        )
        push = wait_push(sub, 1.0)
        assert push is not None
        assert push.event == "concurrency_limit"
        assert push.data["concurrency_limit_exceeded"] is True
        assert push.data["agent_name"] == "Praxis"
    finally:
        unsubscribe(sub)


def test_non_concurrency_failure_does_not_publish_alert():
    sub = subscribe()
    try:
        wait_push(sub, 0.05)
        notify_consolidation_failure(
            agent_name="Praxis",
            concurrency_limit_exceeded=False,
            message="network blip",
        )
        assert wait_push(sub, 0.2) is None
    finally:
        unsubscribe(sub)
