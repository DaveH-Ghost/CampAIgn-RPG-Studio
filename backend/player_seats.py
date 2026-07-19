"""Short-lived player seat tokens for /play clients (Studio 1.7.0).

In-memory only — fine for the singleton GM host process. Tokens bind to a
player ``agent_id`` and expire after a TTL.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

DEFAULT_SEAT_TTL_SECONDS = 3600
_MIN_TTL_SECONDS = 60
_MAX_TTL_SECONDS = 24 * 3600


@dataclass
class SeatRecord:
    agent_id: str
    expires_at: float


_seats: dict[str, SeatRecord] = {}


def reset_seats_for_tests() -> None:
    """Clear all seats (tests / session reset)."""
    _seats.clear()


def create_seat(agent_id: str, *, ttl_seconds: int | None = None) -> tuple[str, float]:
    """Mint a new seat token. Returns ``(token, expires_at_unix)``."""
    ttl = DEFAULT_SEAT_TTL_SECONDS if ttl_seconds is None else int(ttl_seconds)
    ttl = max(_MIN_TTL_SECONDS, min(_MAX_TTL_SECONDS, ttl))
    token = secrets.token_urlsafe(24)
    expires_at = time.time() + ttl
    _seats[token] = SeatRecord(agent_id=agent_id, expires_at=expires_at)
    return token, expires_at


def resolve_seat(token: str | None) -> SeatRecord | None:
    """Return a live seat record, or None if missing/expired."""
    if not token:
        return None
    record = _seats.get(token)
    if record is None:
        return None
    if time.time() >= record.expires_at:
        _seats.pop(token, None)
        return None
    return record


def revoke_seat(token: str) -> bool:
    """Remove a seat. Returns True if it existed."""
    return _seats.pop(token, None) is not None
