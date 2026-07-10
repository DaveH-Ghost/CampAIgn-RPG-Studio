"""
In-memory Session holder for the realm-studio demo (single-player, one process).
"""

from __future__ import annotations

import os

from realm_fabric import Area, Session, load_profile

_store: SessionStore | None = None

_DEV_STACK_ENV = "REALM_STUDIO_DEV_STACK"
_DEV_STACK_TILE = (3, 3)
_DEV_STACK_COUNT = 10


def _maybe_dev_stack_seed(session: Session) -> None:
    """
    Temporary dev helper: stack objects on one tile to test grid scrolling.

    Enable: REALM_STUDIO_DEV_STACK=1 uv run realm-studio
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

    def export_session(self) -> dict:
        """Full save document for download."""
        return self._session.to_save_dict()

    def import_session(self, data: dict) -> None:
        """Replace the in-memory session from a save document."""
        self._session = Session.from_snapshot(data)

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
    _store = None
