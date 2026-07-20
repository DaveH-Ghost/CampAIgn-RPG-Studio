"""Initiative HTTP helpers for campaign-rpg-studio (1.7.1)."""

from __future__ import annotations

from campaign_rpg_engine import Session

from backend.initiative import (
    advance_next,
    attach_initiative_to_snapshot,
    public_initiative_from_session,
    put_initiative,
    set_order,
)
from backend.snapshot_compat import normalize_state_snapshot


def _response(session: Session) -> dict[str, object]:
    snap = normalize_state_snapshot(session.snapshot(include_private=True))
    attach_initiative_to_snapshot(snap, session)
    return {
        "ok": True,
        "initiative": public_initiative_from_session(session),
        "snapshot": snap,
    }


def api_put_initiative(
    session: Session,
    *,
    enabled: bool | None = None,
    order: list[str] | None = None,
    index: int | None = None,
) -> dict[str, object]:
    _state, err = put_initiative(session, enabled=enabled, order=order, index=index)
    if err:
        return {"ok": False, "message": err}
    return _response(session)


def api_post_initiative_order(session: Session, order: list[str]) -> dict[str, object]:
    set_order(session, order)
    return _response(session)


def api_post_initiative_next(session: Session) -> dict[str, object]:
    advance_next(session)
    return _response(session)


def api_get_initiative(session: Session) -> dict[str, object]:
    return {
        "ok": True,
        "initiative": public_initiative_from_session(session),
    }
