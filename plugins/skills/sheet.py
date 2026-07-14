"""Read/write agent skills data from private_data JSON."""

from __future__ import annotations

import json
import sys
from typing import Any

dice = sys.modules["studio_plugin_skills.dice"]
state = sys.modules["studio_plugin_skills.state"]


def parse_private_dict(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Parse private_data as a JSON object.

    Returns ``(dict, None)`` on success, ``({}, None)`` for empty,
    or ``(None, error)`` when the blob is non-empty non-JSON.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return {}, None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None, "Agent private_data must be JSON to use the skills plugin."
    if not isinstance(data, dict):
        return None, "Agent private_data JSON must be an object."
    return data, None


def get_sheet(agent) -> dict[str, Any]:
    """Return normalized stats/skills; defaults all stats to 10."""
    blob, err = parse_private_dict(getattr(agent, "private_data", "") or "")
    if err or blob is None:
        return {
            "stats": dice.normalize_stats(None),
            "skills": {},
            "parse_error": err,
            "initialized": False,
        }
    raw = blob.get(state.PRIVATE_KEY)
    initialized = isinstance(raw, dict)
    if not initialized:
        raw = {}
    return {
        "stats": dice.normalize_stats(raw.get("stats")),
        "skills": dice.normalize_skills(raw.get("skills")),
        "parse_error": None,
        "initialized": initialized,
    }


def write_sheet(session, agent, *, stats: dict[str, int], skills: dict[str, int]) -> str | None:
    """Update skills_plugin in private_data. Returns an error message or None."""
    blob, err = parse_private_dict(getattr(agent, "private_data", "") or "")
    if err:
        return err
    assert blob is not None
    blob[state.PRIVATE_KEY] = {
        "stats": dice.normalize_stats(stats),
        "skills": dice.normalize_skills(skills),
    }
    result = session.set_entity_private_data(
        agent.id,
        json.dumps(blob, indent=2, sort_keys=True),
    )
    if not result.ok:
        return result.message
    return None


def init_default_sheet(session, agent) -> dict[str, Any]:
    """
    Write default all-10 stats into private_data if skills_plugin is missing.

    Does not overwrite an existing skills_plugin block.
    """
    blob, err = parse_private_dict(getattr(agent, "private_data", "") or "")
    if err:
        return {"ok": False, "message": err}
    assert blob is not None
    if isinstance(blob.get(state.PRIVATE_KEY), dict):
        return {
            "ok": False,
            "message": (
                f"{agent.name} already has skills_plugin in private_data. "
                "Edit it on the agent form to change values."
            ),
        }
    write_err = write_sheet(
        session,
        agent,
        stats=dice.normalize_stats(None),
        skills={},
    )
    if write_err:
        return {"ok": False, "message": write_err}
    return {
        "ok": True,
        "message": (
            f"Initialized {agent.name} with default stats "
            f"(all {dice.DEFAULT_STAT}). Edit private_data to customize."
        ),
    }
