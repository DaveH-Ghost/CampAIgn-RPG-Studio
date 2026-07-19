"""Player seat minting (GM) and player-scoped play API (Studio 1.7.0)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from backend.player_seats import create_seat, resolve_seat, revoke_seat
from backend.player_view import build_player_view
from backend.schemas import CreateSeatRequest, PlayerTurnRequest
from backend.session_store import get_session_store
from backend.sse import sse_streaming_response
from backend.turn_runner import run_manual_turn

router = APIRouter()


def _seat_token_from_request(
    authorization: Annotated[str | None, Header()] = None,
    seat: Annotated[str | None, Query()] = None,
) -> str:
    if authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            return parts[1].strip()
    if seat and seat.strip():
        return seat.strip()
    raise HTTPException(status_code=401, detail="Missing seat token.")


def _require_seat(
    token: Annotated[str, Depends(_seat_token_from_request)],
) -> tuple[str, str, float]:
    """Return ``(token, agent_id, expires_at)`` or raise 401."""
    record = resolve_seat(token)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid or expired seat token.")
    session = get_session_store().session
    agent = session.get_agent(record.agent_id)
    if agent is None or not agent.is_player:
        revoke_seat(token)
        raise HTTPException(status_code=401, detail="Seat agent is no longer a valid player.")
    return token, record.agent_id, record.expires_at


@router.get("/api/player/stream")
async def player_stream(
    seat: Annotated[tuple[str, str, float], Depends(_require_seat)],
):
    """SSE for seated player clients (auth via Bearer or ``?seat=``)."""
    del seat
    return sse_streaming_response()


@router.post("/api/seats")
def post_create_seat(body: CreateSeatRequest, request: Request) -> dict[str, object]:
    session = get_session_store().session
    agent = session.get_agent(body.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {body.agent_id!r} not found.")
    if not agent.is_player:
        raise HTTPException(
            status_code=400,
            detail=f"Agent {body.agent_id!r} is not a player agent.",
        )
    token, expires_at = create_seat(agent.id, ttl_seconds=body.ttl_seconds)
    base = str(request.base_url).rstrip("/")
    join_url = f"{base}/play/generic/?seat={token}"
    return {
        "ok": True,
        "token": token,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "expires_at": expires_at,
        "join_url": join_url,
    }


@router.delete("/api/seats/{token}")
def delete_seat(token: str) -> dict[str, object]:
    revoked = revoke_seat(token)
    return {"ok": True, "revoked": revoked}


@router.get("/api/player/me")
def get_player_me(
    seat: Annotated[tuple[str, str, float], Depends(_require_seat)],
) -> dict[str, object]:
    _token, agent_id, expires_at = seat
    session = get_session_store().session
    agent = session.get_agent(agent_id)
    assert agent is not None
    return {
        "ok": True,
        "agent_id": agent.id,
        "name": agent.name,
        "expires_at": expires_at,
    }


@router.get("/api/player/view")
def get_player_view(
    seat: Annotated[tuple[str, str, float], Depends(_require_seat)],
) -> dict[str, object]:
    _token, agent_id, expires_at = seat
    session = get_session_store().session
    try:
        view = build_player_view(session, agent_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    view["expires_at"] = expires_at
    return view


@router.get("/api/player/assist")
def get_player_assist(
    seat: Annotated[tuple[str, str, float], Depends(_require_seat)],
) -> dict[str, object]:
    _token, agent_id, _expires = seat
    session = get_session_store().session
    try:
        view = build_player_view(session, agent_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "targets": view.get("assist") or [],
        "social_candidates": view.get("social_candidates") or [],
    }


@router.post("/api/player/turn")
def post_player_turn(
    body: PlayerTurnRequest,
    seat: Annotated[tuple[str, str, float], Depends(_require_seat)],
) -> dict[str, object]:
    _token, agent_id, _expires = seat
    session = get_session_store().session
    result = run_manual_turn(
        session,
        dict(body.compound_turn),
        agent_id=agent_id,
    )
    if not result.get("ok"):
        return {
            "ok": False,
            "message": result.get("message") or "Turn failed.",
        }
    try:
        view = build_player_view(session, agent_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "message": result.get("message") or "Turn applied.",
        "steps": result.get("steps") or [],
        "view": view,
    }
