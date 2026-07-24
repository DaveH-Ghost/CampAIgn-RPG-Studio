"""Session-scoped routes: health, state, active agent/area, session import/export, events."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.plugin_registry import merged_interact_template_vars
from backend.schemas import ActiveAgentRequest, ActiveAreaRequest, EventRequest
from backend.session_store import get_session_store
from backend.snapshot_compat import normalize_state_snapshot
from backend.sse import sse_streaming_response
from backend.version import engine_version, studio_version

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, object]:
    from backend.hosting import get_hosting_settings

    hosting = get_hosting_settings()
    return {
        "ok": True,
        "version": studio_version(),
        "campaign_rpg_engine_version": engine_version(),
        "listen_host": hosting["listen_host"],
        "listen_port": hosting["listen_port"],
        "public_base_url": hosting["public_base_url"],
    }


@router.get("/api/session/stream")
async def session_stream():
    """Server-Sent Events: push when the live session changes (GM clients)."""
    return sse_streaming_response()


@router.get("/api/interact-template-vars")
def get_interact_template_vars() -> dict[str, object]:
    return {"vars": merged_interact_template_vars(get_session_store().session)}


@router.get("/api/state")
def get_state() -> dict:
    snap = get_session_store().session.snapshot(include_private=True)
    return normalize_state_snapshot(snap)


@router.post("/api/active-agent")
def post_active_agent(body: ActiveAgentRequest) -> dict[str, object]:
    result = get_session_store().session.set_active_agent(body.name_or_id)
    return {"ok": result.ok, "message": result.message}


@router.post("/api/active-area")
def post_active_area(body: ActiveAreaRequest) -> dict[str, object]:
    session = get_session_store().session
    result = session.set_active_area(body.area_id)
    payload: dict[str, object] = {"ok": result.ok, "message": result.message}
    if result.ok:
        payload["snapshot"] = normalize_state_snapshot(session.snapshot(include_private=True))
    return payload


@router.get("/api/session/export")
def export_session_route() -> JSONResponse:
    store = get_session_store()
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    filename = f"realm-session-{stamp}.json"
    return JSONResponse(
        content=store.export_session(),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/api/session/import")
async def import_session_route(body: dict) -> dict[str, object]:
    store = get_session_store()
    try:
        store.import_session(body)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session = store.session
    agent = session.get_active_agent()
    return {
        "ok": True,
        "message": (
            f"Session loaded (turn {session.session_turn}, "
            f"active agent {agent.name}, {len(session.areas)} area(s))."
        ),
    }


@router.post("/api/event")
def post_event(body: EventRequest) -> dict[str, object]:
    session = get_session_store().session
    result = session.emit_area_event(body.text, agent_ids=body.agent_ids)
    payload: dict[str, object] = {"ok": result.ok, "message": result.message}
    if result.ok:
        payload["snapshot"] = normalize_state_snapshot(session.snapshot(include_private=True))
    return payload
