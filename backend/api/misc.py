"""Miscellaneous routes: catalogs, command CLI, vision/coordinate config, decorations."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.command_dispatch import dispatch_command
from backend.coordinate_mode_api import put_coordinate_mode as api_put_coordinate_mode
from backend.decoration_assets_api import upload_decoration_asset
from backend.decorations_api import create_decoration as api_create_decoration
from backend.decorations_api import delete_decoration as api_delete_decoration
from backend.decorations_api import reorder_decoration as api_reorder_decoration
from backend.decorations_api import update_decoration as api_update_decoration
from backend.interaction_handlers_api import get_interaction_handlers_catalog
from backend.memory_modules_api import get_memory_modules_catalog
from backend.plugins_api import get_player_turn_assist_route
from backend.schemas import (
    CommandRequest,
    CoordinateModeRequest,
    CreateDecorationRequest,
    DeleteDecorationRequest,
    ReorderDecorationRequest,
    UpdateDecorationRequest,
    VisionUnitsRequest,
)
from backend.session_store import get_session_store
from backend.snapshot_compat import normalize_state_snapshot
from backend.turn_verbs_api import get_turn_verbs_catalog
from backend.vision_units_api import put_vision_units as api_put_vision_units

router = APIRouter()


@router.get("/api/interaction-handlers")
def get_interaction_handlers() -> dict[str, object]:
    return get_interaction_handlers_catalog(get_session_store().session)


@router.get("/api/turn-verbs")
def get_turn_verbs() -> dict[str, object]:
    return get_turn_verbs_catalog(get_session_store().session)


@router.get("/api/player-turn-assist")
def get_player_turn_assist() -> dict[str, object]:
    return get_player_turn_assist_route(get_session_store().session)


@router.get("/api/memory-modules")
def get_memory_modules_route() -> dict[str, object]:
    return get_memory_modules_catalog()


@router.put("/api/vision-units")
def put_vision_units_route(body: VisionUnitsRequest) -> dict[str, object]:
    return api_put_vision_units(
        get_session_store().session,
        units=body.units,
        units_per_tile=body.units_per_tile,
    )


@router.put("/api/coordinate-mode")
def put_coordinate_mode_route(body: CoordinateModeRequest) -> dict[str, object]:
    return api_put_coordinate_mode(
        get_session_store().session,
        mode=body.mode,
    )


@router.post("/api/command")
def post_command(body: CommandRequest) -> dict[str, object]:
    """Run a stepper-style command (create/edit/delete, listings)."""
    store = get_session_store()
    session = store.session
    result = dispatch_command(session, body.line.strip())
    payload: dict[str, object] = {"ok": result.ok, "message": result.message}
    if result.ok:
        store.clear_undo()
        payload["snapshot"] = normalize_state_snapshot(session.snapshot(include_private=True))
        payload["can_undo"] = False
        payload["undo_remaining"] = 0
    return payload


@router.post("/api/decorations")
def post_create_decoration(body: CreateDecorationRequest) -> dict[str, object]:
    session = get_session_store().session
    result = api_create_decoration(
        session,
        kind=body.kind,
        image=body.image,
        area_id=body.area_id,
        x=body.x,
        y=body.y,
        width=body.width,
        height=body.height,
        z_index=body.z_index,
        repeat=body.repeat,
        decoration_id=body.decoration_id,
        label=body.label,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Create failed"))
    return result


@router.put("/api/decorations")
def put_update_decoration(body: UpdateDecorationRequest) -> dict[str, object]:
    session = get_session_store().session
    result = api_update_decoration(
        session,
        decoration_id=body.decoration_id,
        area_id=body.area_id,
        image=body.image,
        x=body.x,
        y=body.y,
        width=body.width,
        height=body.height,
        z_index=body.z_index,
        repeat=body.repeat,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Update failed"))
    return result


@router.delete("/api/decorations")
def delete_decoration_route(body: DeleteDecorationRequest) -> dict[str, object]:
    session = get_session_store().session
    result = api_delete_decoration(
        session,
        decoration_id=body.decoration_id,
        area_id=body.area_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Delete failed"))
    return result


@router.post("/api/decorations/reorder")
def post_reorder_decoration(body: ReorderDecorationRequest) -> dict[str, object]:
    session = get_session_store().session
    result = api_reorder_decoration(
        session,
        decoration_id=body.decoration_id,
        direction=body.direction,
        area_id=body.area_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Reorder failed"))
    return result


@router.post("/api/decoration-assets/upload")
async def upload_decoration_asset_route(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    raw = await file.read()
    try:
        return upload_decoration_asset(data=raw, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
