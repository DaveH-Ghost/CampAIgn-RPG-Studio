"""SSE helpers for session change streams."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi.responses import StreamingResponse

from backend.session_events import subscribe, unsubscribe, wait_revision
from backend.session_store import get_session_store

_KEEPALIVE_SECONDS = 15.0
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def session_change_event_stream() -> AsyncIterator[str]:
    """Yield SSE payloads whenever the Studio session is mutated."""
    sub = subscribe()
    last_sent = -1
    try:
        while True:
            rev = await asyncio.to_thread(wait_revision, sub, _KEEPALIVE_SECONDS)
            if rev is None:
                yield ": keepalive\n\n"
                continue
            if rev == last_sent:
                continue
            last_sent = rev
            session = get_session_store().session
            payload = {
                "revision": rev,
                "session_turn": session.session_turn,
                "active_agent_id": session.active_agent_id,
                "active_area_id": session.active_area_id,
            }
            yield f"event: change\ndata: {json.dumps(payload)}\n\n"
    finally:
        unsubscribe(sub)


def sse_streaming_response() -> StreamingResponse:
    return StreamingResponse(
        session_change_event_stream(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
