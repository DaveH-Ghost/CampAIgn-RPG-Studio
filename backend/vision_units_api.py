"""Vision units API helpers for realm-studio (V0.4.1c)."""

from __future__ import annotations

from backend.snapshot_compat import normalize_state_snapshot
from realm_fabric import Session


def put_vision_units(
    session: Session,
    *,
    units: str,
    units_per_tile: int | None,
) -> dict[str, object]:
    err = session.set_vision_units(units, units_per_tile)
    if err:
        return {"ok": False, "message": err}
    return {
        "ok": True,
        "vision_units": session.vision_units,
        "vision_units_per_tile": session.vision_units_per_tile,
        "snapshot": normalize_state_snapshot(session.snapshot(include_private=True)),
    }
