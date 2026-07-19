"""Lorebook routes: CRUD, scan config, upload/download, demo loader."""

from __future__ import annotations

import json

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from backend.lorebooks_api import (
    create_lorebook,
    delete_lorebook,
    export_lorebook_download,
    get_lorebook,
    get_lorebook_scan_config,
    list_lorebooks,
    load_demo_lorebook,
    put_lorebook,
    put_lorebook_scan_config,
    upload_lorebook,
)
from backend.session_store import get_session_store

router = APIRouter()


@router.get("/api/lorebooks")
def get_lorebooks_route() -> dict[str, object]:
    return list_lorebooks(get_session_store().session)


@router.post("/api/lorebooks")
def create_lorebook_route(body: dict | None = None) -> dict[str, object]:
    result = create_lorebook(get_session_store().session, body or {})
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Create failed"))
    return result


@router.post("/api/lorebooks/load-demo")
def load_demo_lorebook_route() -> dict[str, object]:
    result = load_demo_lorebook(get_session_store().session)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.get("/api/lorebooks/scan-config")
def get_lorebook_scan_config_route(agent_id: str | None = None) -> dict[str, object]:
    result = get_lorebook_scan_config(
        get_session_store().session,
        agent_id=agent_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.put("/api/lorebooks/scan-config")
def put_lorebook_scan_config_route(body: dict) -> dict[str, object]:
    result = put_lorebook_scan_config(get_session_store().session, body)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Update failed"))
    return result


@router.get("/api/lorebooks/{book_id}")
def get_lorebook_route(book_id: str) -> dict[str, object]:
    result = get_lorebook(get_session_store().session, book_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.get("/api/lorebooks/{book_id}/download")
def download_lorebook_route(book_id: str) -> Response:
    result = export_lorebook_download(get_session_store().session, book_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    filename = str(result["filename"])
    body = json.dumps(result["payload"], indent=2, ensure_ascii=False)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/api/lorebooks/{book_id}")
def put_lorebook_route(book_id: str, body: dict) -> dict[str, object]:
    result = put_lorebook(get_session_store().session, book_id, body)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Update failed"))
    return result


@router.delete("/api/lorebooks/{book_id}")
def delete_lorebook_route(book_id: str) -> dict[str, object]:
    result = delete_lorebook(get_session_store().session, book_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result


@router.post("/api/lorebooks/upload")
async def upload_lorebook_route(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Upload must be a .json file.")
    raw = await file.read()
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="Lorebook file must be UTF-8 text."
        ) from exc
    result = upload_lorebook(
        get_session_store().session,
        source=source,
        filename=file.filename,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Upload failed"))
    return result
