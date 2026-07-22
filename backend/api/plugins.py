"""Plugin routes: catalog, enable/disable, panel, action, upload."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.plugin_upload import upload_plugin
from backend.plugins_api import (
    get_entity_form_sections_route,
    get_plugin_panel_route,
    get_plugins_catalog,
    post_disable_plugin,
    post_enable_plugin,
    post_merge_entity_form_private_data,
    post_plugin_action,
)
from backend.session_store import get_session_store

router = APIRouter()


@router.get("/api/plugins")
def get_plugins_route() -> dict[str, object]:
    return get_plugins_catalog(get_session_store().session)


@router.get("/api/entity-form-sections")
def get_entity_form_sections_api(kind: str, entity_id: str | None = None) -> dict[str, object]:
    result = get_entity_form_sections_route(
        get_session_store().session,
        kind,
        entity_id=entity_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Bad request"))
    return result


@router.post("/api/entity-form-sections/merge")
def post_entity_form_sections_merge(body: dict) -> dict[str, object]:
    result = post_merge_entity_form_private_data(get_session_store().session, body)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Merge failed"))
    return result


@router.post("/api/plugins/{plugin_id}/enable")
def enable_plugin_route(plugin_id: str) -> dict[str, object]:
    result = post_enable_plugin(get_session_store().session, plugin_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Enable failed"))
    return result


@router.post("/api/plugins/{plugin_id}/disable")
def disable_plugin_route(plugin_id: str) -> dict[str, object]:
    result = post_disable_plugin(get_session_store().session, plugin_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Disable failed"))
    return result


@router.get("/api/plugins/{plugin_id}/panel")
def get_plugin_panel_api_route(plugin_id: str) -> dict[str, object]:
    result = get_plugin_panel_route(get_session_store().session, plugin_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.post("/api/plugins/{plugin_id}/action")
def post_plugin_action_route(plugin_id: str, body: dict) -> dict[str, object]:
    result = post_plugin_action(get_session_store().session, plugin_id, body)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Action failed"))
    return result


@router.post("/api/plugins/upload")
async def upload_plugin_route(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    lower = file.filename.lower()
    if not (lower.endswith(".py") or lower.endswith(".zip")):
        raise HTTPException(
            status_code=400, detail="Upload must be a .py file or .zip package."
        )
    raw = await file.read()
    try:
        if lower.endswith(".py"):
            source = raw.decode("utf-8")
        else:
            source = raw
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Plugin file must be UTF-8 text.") from exc
    try:
        if lower.endswith(".py"):
            return upload_plugin(source=source, filename=file.filename)
        return upload_plugin(source=raw, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
