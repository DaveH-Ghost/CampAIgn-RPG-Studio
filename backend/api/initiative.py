"""Initiative turn-order routes (Studio 1.7.1)."""

from __future__ import annotations

from fastapi import APIRouter

from backend.initiative_api import (
    api_get_initiative,
    api_post_initiative_next,
    api_post_initiative_order,
    api_put_initiative,
)
from backend.schemas import InitiativeOrderRequest, InitiativePutRequest
from backend.session_store import get_session_store

router = APIRouter()


@router.get("/api/initiative")
def get_initiative() -> dict[str, object]:
    return api_get_initiative(get_session_store().session)


@router.put("/api/initiative")
def put_initiative(body: InitiativePutRequest) -> dict[str, object]:
    return api_put_initiative(
        get_session_store().session,
        enabled=body.enabled,
        order=body.order,
        index=body.index,
    )


@router.post("/api/initiative/order")
def post_initiative_order(body: InitiativeOrderRequest) -> dict[str, object]:
    return api_post_initiative_order(get_session_store().session, body.order)


@router.post("/api/initiative/next")
def post_initiative_next() -> dict[str, object]:
    return api_post_initiative_next(get_session_store().session)
