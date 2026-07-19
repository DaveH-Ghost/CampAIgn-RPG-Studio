"""Coordinate mode API helpers for campaign-rpg-studio."""

from __future__ import annotations

from campaign_rpg_engine import Session
from campaign_rpg_engine.coordinate_mode import COORDINATE_MODE_RELATIVE

from backend.snapshot_compat import normalize_state_snapshot


def put_coordinate_mode(session: Session, *, mode: str) -> dict[str, object]:
    err = session.set_coordinate_mode(mode)
    if err:
        return {"ok": False, "message": err}

    if session.coordinate_mode == COORDINATE_MODE_RELATIVE:
        if not session.vision_units.strip():
            session.set_vision_units("ft", session.vision_units_per_tile or 5)
        elif session.vision_units_per_tile is None:
            session.set_vision_units(session.vision_units, 5)

    return {
        "ok": True,
        "coordinate_mode": session.coordinate_mode,
        "vision_units": session.vision_units,
        "vision_units_per_tile": session.vision_units_per_tile,
        "snapshot": normalize_state_snapshot(session.snapshot(include_private=True)),
    }
