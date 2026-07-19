"""Entity and area template routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.area_templates_api import (
    delete_area_template,
    download_area_template_file,
    export_area_template_download,
    get_area_template,
    list_area_templates,
    save_area_from_world,
    save_area_template,
    spawn_area_from_template_data,
    spawn_area_template,
)
from backend.entity_templates_api import (
    delete_entity_template,
    download_entity_template_file,
    export_entity_template_download,
    get_entity_template,
    list_entity_templates,
    save_entity_from_world,
    save_entity_template,
    spawn_entity_from_template_data,
    spawn_entity_template,
)
from backend.schemas import (
    AreaTemplateImportRequest,
    AreaTemplateSaveRequest,
    AreaTemplateSpawnFromBodyRequest,
    AreaTemplateSpawnRequest,
    EntityTemplateImportRequest,
    EntityTemplateSaveRequest,
    EntityTemplateSpawnFromBodyRequest,
    EntityTemplateSpawnRequest,
)
from backend.session_store import get_session_store

router = APIRouter()


@router.get("/api/entity-templates")
def get_entity_templates_route() -> dict[str, object]:
    return list_entity_templates()


@router.get("/api/entity-templates/{template_id}")
def get_entity_template_route(template_id: str) -> dict[str, object]:
    result = get_entity_template(template_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.post("/api/entity-templates/import")
def import_entity_template_route(body: EntityTemplateImportRequest) -> dict[str, object]:
    result = save_entity_template(body.template, filename=body.filename)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Import failed"))
    return result


@router.post("/api/entity-templates/save-from-entity")
def save_entity_template_route(body: EntityTemplateSaveRequest) -> dict[str, object]:
    result = save_entity_from_world(
        get_session_store().session,
        kind=body.kind,
        entity_id=body.entity_id,
        filename=body.filename,
        include_memory=body.include_memory,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Save failed"))
    return result


@router.post("/api/entity-templates/export-from-entity")
def export_entity_template_route(body: EntityTemplateSaveRequest) -> Response:
    result = export_entity_template_download(
        get_session_store().session,
        kind=body.kind,
        entity_id=body.entity_id,
        filename=body.filename,
        include_memory=body.include_memory,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Export failed"))
    filename = str(result["filename"])
    payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/entity-templates/{template_id}/download")
def download_entity_template_route(template_id: str) -> Response:
    result = download_entity_template_file(template_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    filename = str(result["filename"])
    payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/entity-templates/spawn-from-template")
def spawn_entity_from_template_route(
    body: EntityTemplateSpawnFromBodyRequest,
) -> dict[str, object]:
    result = spawn_entity_from_template_data(
        get_session_store().session,
        body.template,
        position=body.position,
        area_id=body.area_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
    return result


@router.post("/api/entity-templates/{template_id}/spawn")
def spawn_entity_template_route(
    template_id: str,
    body: EntityTemplateSpawnRequest,
) -> dict[str, object]:
    result = spawn_entity_template(
        get_session_store().session,
        template_id,
        position=body.position,
        area_id=body.area_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
    return result


@router.delete("/api/entity-templates/{template_id}")
def delete_entity_template_route(template_id: str) -> dict[str, object]:
    result = delete_entity_template(template_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.get("/api/area-templates")
def get_area_templates_route() -> dict[str, object]:
    return list_area_templates()


@router.get("/api/area-templates/{template_id}")
def get_area_template_route(template_id: str) -> dict[str, object]:
    result = get_area_template(template_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.post("/api/area-templates/import")
def import_area_template_route(body: AreaTemplateImportRequest) -> dict[str, object]:
    result = save_area_template(body.template, filename=body.filename)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Import failed"))
    return result


@router.post("/api/area-templates/save-from-area")
def save_area_template_route(body: AreaTemplateSaveRequest) -> dict[str, object]:
    result = save_area_from_world(
        get_session_store().session,
        area_id=body.area_id,
        filename=body.filename,
        name=body.name,
        include_hidden_objects=body.include_hidden_objects,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Save failed"))
    return result


@router.post("/api/area-templates/export-from-area")
def export_area_template_route(body: AreaTemplateSaveRequest) -> Response:
    result = export_area_template_download(
        get_session_store().session,
        area_id=body.area_id,
        filename=body.filename,
        name=body.name,
        include_hidden_objects=body.include_hidden_objects,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Export failed"))
    filename = str(result["filename"])
    payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/area-templates/{template_id}/download")
def download_area_template_route(template_id: str) -> Response:
    result = download_area_template_file(template_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    filename = str(result["filename"])
    payload = json.dumps(result["template"], indent=2, ensure_ascii=False)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/area-templates/spawn-from-template")
def spawn_area_from_template_route(
    body: AreaTemplateSpawnFromBodyRequest,
) -> dict[str, object]:
    result = spawn_area_from_template_data(
        get_session_store().session,
        body.template,
        area_id=body.area_id,
        mode=body.mode,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
    return result


@router.post("/api/area-templates/{template_id}/spawn")
def spawn_area_template_route(
    template_id: str,
    body: AreaTemplateSpawnRequest,
) -> dict[str, object]:
    result = spawn_area_template(
        get_session_store().session,
        template_id,
        area_id=body.area_id,
        mode=body.mode,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Spawn failed"))
    return result


@router.delete("/api/area-templates/{template_id}")
def delete_area_template_route(template_id: str) -> dict[str, object]:
    result = delete_area_template(template_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result
