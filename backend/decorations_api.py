"""Decoration CRUD helpers for campaign-rpg-studio (V1.3.0)."""

from __future__ import annotations

from campaign_rpg_engine import DecorationMutationResult, Session

from backend.snapshot_compat import normalize_state_snapshot


def decoration_mutation_response(
    session: Session, result: DecorationMutationResult
) -> dict[str, object]:
    payload: dict[str, object] = {"ok": result.ok, "message": result.message}
    if result.ok:
        payload["snapshot"] = normalize_state_snapshot(session.snapshot(include_private=True))
        if result.decoration is not None:
            from campaign_rpg_engine.snapshot import serialize_decoration

            payload["decoration"] = serialize_decoration(result.decoration)
    return payload


def create_decoration(
    session: Session,
    *,
    kind: str,
    image: str,
    area_id: str | None = None,
    x: int = 0,
    y: int = 0,
    width: int = 0,
    height: int = 0,
    z_index: int | None = None,
    repeat: str = "repeat",
    decoration_id: str | None = None,
    label: str = "decor",
) -> dict[str, object]:
    return decoration_mutation_response(
        session,
        session.create_decoration(
            kind=kind,
            image=image,
            area_id=area_id,
            x=x,
            y=y,
            width=width,
            height=height,
            z_index=z_index,
            repeat=repeat,
            decoration_id=decoration_id,
            label=label,
        ),
    )


def update_decoration(
    session: Session,
    *,
    decoration_id: str,
    area_id: str | None = None,
    image: str | None = None,
    x: int | None = None,
    y: int | None = None,
    width: int | None = None,
    height: int | None = None,
    z_index: int | None = None,
    repeat: str | None = None,
) -> dict[str, object]:
    return decoration_mutation_response(
        session,
        session.update_decoration(
            decoration_id,
            area_id=area_id,
            image=image,
            x=x,
            y=y,
            width=width,
            height=height,
            z_index=z_index,
            repeat=repeat,
        ),
    )


def delete_decoration(
    session: Session,
    *,
    decoration_id: str,
    area_id: str | None = None,
) -> dict[str, object]:
    return decoration_mutation_response(
        session,
        session.delete_decoration(decoration_id, area_id=area_id),
    )


def reorder_decoration(
    session: Session,
    *,
    decoration_id: str,
    direction: str,
    area_id: str | None = None,
) -> dict[str, object]:
    return decoration_mutation_response(
        session,
        session.reorder_decoration(
            decoration_id,
            direction,
            area_id=area_id,
        ),
    )
