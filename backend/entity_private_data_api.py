"""Set entity private_data without CLI (custom-app field, V0.6.0 cleanup)."""

from __future__ import annotations

from backend.snapshot_compat import normalize_state_snapshot


def put_entity_private_data(session, *, entity_id: str, private_data: str) -> dict[str, object]:
    result = session.set_entity_private_data(entity_id, private_data)
    payload: dict[str, object] = {"ok": result.ok, "message": result.message}
    if result.ok:
        payload["snapshot"] = normalize_state_snapshot(
            session.snapshot(include_private=True)
        )
    return payload
