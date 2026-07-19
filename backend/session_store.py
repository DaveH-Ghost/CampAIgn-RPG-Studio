"""
In-memory Session holder for the campaign-rpg-studio demo (single-player, one process).

Single-session GM host: this module owns exactly one engine ``Session`` for the
lifetime of the server process, exposed as a lazy process singleton via
``get_session_store()``. There is no per-request or per-user isolation today --
every request operates on the same shared session. Multi-session support (keyed
stores, per-session lifecycles) is a deliberate future step and intentionally not
implemented here.
"""

from __future__ import annotations

import os
from collections import deque
from typing import Any

from campaign_rpg_engine import Area, Session, load_profile

from backend.snapshot_compat import normalize_state_snapshot

_store: SessionStore | None = None

_DEV_STACK_ENV = "REALM_STUDIO_DEV_STACK"
_DEV_STACK_TILE = (3, 3)
_DEV_STACK_COUNT = 10
UNDO_STACK_MAX = 20


def _maybe_dev_stack_seed(session: Session) -> None:
    """
    Temporary dev helper: stack objects on one tile to test grid scrolling.

    Enable: REALM_STUDIO_DEV_STACK=1 uv run campaign-rpg-studio
    Remove when no longer needed for UI testing.
    """
    flag = os.environ.get(_DEV_STACK_ENV, "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return
    x, y = _DEV_STACK_TILE
    for i in range(1, _DEV_STACK_COUNT + 1):
        session.create_object(
            name=f"Stack{i}",
            passive_description=f"Stack test item {i}.",
            description=f"Dev stack object {i}.",
            position=(x, y),
        )


def _seed_studio_hall(session: Session) -> None:
    """Second empty area so the area dropdown is exercisable (V0.4.0c2)."""
    if "hall" not in session.areas:
        session.areas["hall"] = Area(
            area_description="A narrow stone hall with worn flagstones.",
        )


class SessionStore:
    """Owns one engine ``Session`` for the lifetime of the server process."""

    def __init__(self) -> None:
        from reference_handlers import register_reference_handlers

        register_reference_handlers()
        profile = load_profile("default_compound")
        self._session = Session.from_profile(profile)
        _seed_studio_hall(self._session)
        _maybe_dev_stack_seed(self._session)
        self._undo_stack: deque[dict[str, Any]] = deque(maxlen=UNDO_STACK_MAX)

    def export_session(self) -> dict:
        """Full save document for download."""
        return self._session.to_save_dict()

    def import_session(self, data: dict) -> None:
        """Replace the in-memory session from a save document."""
        from backend.plugins_api import on_session_imported

        self._session = Session.from_snapshot(data)
        on_session_imported(self._session)
        self.clear_undo()

    def capture_checkpoint(self) -> dict[str, Any]:
        """Full save-dict snapshot for turn undo."""
        return self._session.to_save_dict()

    def push_undo(self, checkpoint: dict[str, Any]) -> None:
        """Record a pre-turn checkpoint after a successful turn."""
        self._undo_stack.append(checkpoint)

    def clear_undo(self) -> None:
        """Drop all turn undo checkpoints."""
        self._undo_stack.clear()

    @property
    def undo_remaining(self) -> int:
        return len(self._undo_stack)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def undo_status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "can_undo": self.can_undo,
            "undo_remaining": self.undo_remaining,
        }

    def undo_turn(self) -> dict[str, Any]:
        """Restore the most recent pre-turn checkpoint, if any."""
        if not self._undo_stack:
            return {
                "ok": False,
                "message": "Nothing to undo.",
                "can_undo": False,
                "undo_remaining": 0,
            }

        from backend.plugins_api import on_session_imported

        checkpoint = self._undo_stack.pop()
        self._session = Session.from_snapshot(checkpoint)
        on_session_imported(self._session)
        turn = self._session.session_turn
        return {
            "ok": True,
            "message": f"Undid last turn (restored to session turn {turn}).",
            "snapshot": normalize_state_snapshot(self._session.snapshot(include_private=True)),
            "can_undo": self.can_undo,
            "undo_remaining": self.undo_remaining,
        }

    @property
    def session(self) -> Session:
        return self._session


def get_session_store() -> SessionStore:
    """Return the process-wide session store (lazy singleton)."""
    global _store
    if _store is None:
        _store = SessionStore()
    return _store


def reset_session_store() -> None:
    """Reset store (tests only)."""
    global _store
    from backend.player_seats import reset_seats_for_tests
    from backend.session_events import reset_session_events_for_tests

    reset_seats_for_tests()
    reset_session_events_for_tests()
    _store = None
