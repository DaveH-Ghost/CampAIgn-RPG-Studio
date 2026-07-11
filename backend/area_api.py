"""Area CRUD helpers for campaign-rpg-studio (V0.4.0c2)."""

from __future__ import annotations

from campaign_rpg_engine import Session, WorldMutationResult

from backend.snapshot_compat import normalize_state_snapshot


def area_mutation_response(session: Session, result: WorldMutationResult) -> dict[str, object]:
    payload: dict[str, object] = {"ok": result.ok, "message": result.message}
    if result.ok:
        payload["snapshot"] = normalize_state_snapshot(
            session.snapshot(include_private=True)
        )
    return payload


def create_area(
    session: Session, *, area_id: str, description: str, width: int, height: int
) -> dict[str, object]:
    return area_mutation_response(
        session,
        session.create_area(
            area_id,
            description=description,
            width=width,
            height=height,
        ),
    )


def edit_area(
    session: Session,
    *,
    area_id: str,
    description: str | None,
    width: int | None,
    height: int | None,
) -> dict[str, object]:
    if description is None and width is None and height is None:
        return {
            "ok": False,
            "message": "edit-area requires at least one field to change.",
        }
    return area_mutation_response(
        session,
        session.edit_area(
            area_id,
            description=description,
            width=width,
            height=height,
        ),
    )


def delete_area(session: Session, *, area_id: str) -> dict[str, object]:
    return area_mutation_response(session, session.delete_area(area_id))
