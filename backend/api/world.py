"""World editing routes: area CRUD and app-owned entity private data."""

from __future__ import annotations

from fastapi import APIRouter

from backend.area_api import create_area as api_create_area
from backend.area_api import delete_area as api_delete_area
from backend.area_api import edit_area as api_edit_area
from backend.entity_private_data_api import put_entity_private_data
from backend.schemas import (
    CreateAreaRequest,
    DeleteAreaRequest,
    EditAreaRequest,
    EntityPrivateDataRequest,
)
from backend.session_store import get_session_store

router = APIRouter()


@router.put("/api/entity-private-data")
def put_entity_private_data_route(body: EntityPrivateDataRequest) -> dict[str, object]:
    """Set app-owned private_data on an agent or object (not CLI / LLM)."""
    return put_entity_private_data(
        get_session_store().session,
        entity_id=body.entity_id.strip(),
        private_data=body.private_data,
    )


@router.post("/api/create-area")
def post_create_area(body: CreateAreaRequest) -> dict[str, object]:
    """Create a new empty area (same pattern as /api/event)."""
    session = get_session_store().session
    return api_create_area(
        session,
        area_id=body.area_id.strip().lower(),
        description=body.description,
        width=body.width,
        height=body.height,
    )


@router.post("/api/edit-area")
def post_edit_area(body: EditAreaRequest) -> dict[str, object]:
    """Edit an area description and/or grid size."""
    session = get_session_store().session
    return api_edit_area(
        session,
        area_id=body.area_id.strip().lower(),
        description=body.description,
        width=body.width,
        height=body.height,
    )


@router.post("/api/delete-area")
def post_delete_area(body: DeleteAreaRequest) -> dict[str, object]:
    """Delete an empty area."""
    session = get_session_store().session
    return api_delete_area(session, area_id=body.area_id.strip().lower())
