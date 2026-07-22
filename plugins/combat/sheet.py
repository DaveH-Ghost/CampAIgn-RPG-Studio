"""Parse combat item private_data and agent HP sheets."""

from __future__ import annotations

import json
import sys
from typing import Any

state = sys.modules["studio_plugin_combat.state"]

WEAPON_SLOT = "weapon"
ARMOR_SLOT = "armor"
UNARMED_ACTION = "unarmed"
UNARMED_RANGE = 1
UNARMED_STAT = "STR"
UNARMED_ACCURACY = 0
UNARMED_DAMAGE = "1d4"


def parse_private_dict(text: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = (text or "").strip()
    if not cleaned:
        return {}, None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None, "private_data must be JSON to use the combat plugin."
    if not isinstance(data, dict):
        return None, "private_data JSON must be an object."
    return data, None


def _parse_req(raw: Any) -> dict[str, int]:
    req: dict[str, int] = {}
    if not isinstance(raw, dict):
        return req
    for key, value in raw.items():
        name = str(key).strip().upper()
        if not name:
            continue
        try:
            req[name] = int(value)
        except (TypeError, ValueError):
            continue
    return req


def parse_item_combat(item: dict[str, Any]) -> dict[str, Any] | None:
    """Return normalized combat_plugin block from an inventory item, or None."""
    blob, err = parse_private_dict(str(item.get("private_data") or ""))
    if err or blob is None:
        return None
    raw = blob.get(state.PRIVATE_KEY)
    if not isinstance(raw, dict):
        return None
    slot = str(raw.get("slot") or "").strip().lower()
    if slot not in (WEAPON_SLOT, ARMOR_SLOT):
        return None
    req = _parse_req(raw.get("req"))
    if slot == WEAPON_SLOT:
        # Optional legacy field; attack verbs come from Manage actions (combat_attack).
        action_raw = raw.get("action")
        action = (
            str(action_raw).strip()
            if action_raw is not None and str(action_raw).strip()
            else None
        )
        try:
            range_val = max(0, int(raw.get("range", 1)))
        except (TypeError, ValueError):
            range_val = 1
        attack_stat = str(raw.get("attack_stat") or "STR").strip().upper() or "STR"
        try:
            accuracy = int(raw.get("accuracy_bonus", 0))
        except (TypeError, ValueError):
            accuracy = 0
        damage = str(raw.get("damage") or "1d4").strip() or "1d4"
        out = {
            "slot": WEAPON_SLOT,
            "range": range_val,
            "attack_stat": attack_stat,
            "accuracy_bonus": accuracy,
            "damage": damage,
            "req": req,
        }
        if action:
            out["action"] = action
        return out
    try:
        base_ac = int(raw.get("base_ac", 10))
    except (TypeError, ValueError):
        base_ac = 10
    ac_stat = str(raw.get("ac_stat") or "").strip().upper() or None
    ac_stat_cap: int | None
    if "ac_stat_cap" in raw and raw.get("ac_stat_cap") is not None:
        try:
            ac_stat_cap = int(raw.get("ac_stat_cap"))
        except (TypeError, ValueError):
            ac_stat_cap = None
    else:
        ac_stat_cap = None
    return {
        "slot": ARMOR_SLOT,
        "base_ac": base_ac,
        "ac_stat": ac_stat,
        "ac_stat_cap": ac_stat_cap,
        "req": req,
    }


def unarmed_profile() -> dict[str, Any]:
    return {
        "slot": WEAPON_SLOT,
        "action": UNARMED_ACTION,
        "range": UNARMED_RANGE,
        "attack_stat": UNARMED_STAT,
        "accuracy_bonus": UNARMED_ACCURACY,
        "damage": UNARMED_DAMAGE,
        "req": {},
        "name": "Unarmed",
        "item_id": None,
    }


def get_hp_block(agent) -> dict[str, Any]:
    blob, err = parse_private_dict(getattr(agent, "private_data", "") or "")
    if err or blob is None:
        return {
            "hp": None,
            "max_hp": None,
            "initialized": False,
            "parse_error": err,
        }
    raw = blob.get(state.PRIVATE_KEY)
    if not isinstance(raw, dict):
        return {
            "hp": None,
            "max_hp": None,
            "initialized": False,
            "parse_error": None,
        }
    try:
        hp = int(raw["hp"]) if "hp" in raw else None
    except (TypeError, ValueError):
        hp = None
    try:
        max_hp = int(raw["max_hp"]) if "max_hp" in raw else None
    except (TypeError, ValueError):
        max_hp = None
    return {
        "hp": hp,
        "max_hp": max_hp,
        "initialized": hp is not None,
        "parse_error": None,
    }


def write_hp(session, agent, *, hp: int, max_hp: int) -> str | None:
    blob, err = parse_private_dict(getattr(agent, "private_data", "") or "")
    if err:
        return err
    assert blob is not None
    existing = blob.get(state.PRIVATE_KEY)
    block = dict(existing) if isinstance(existing, dict) else {}
    block["hp"] = int(hp)
    block["max_hp"] = int(max_hp)
    blob[state.PRIVATE_KEY] = block
    result = session.set_entity_private_data(
        agent.id,
        json.dumps(blob, indent=2, sort_keys=True),
    )
    if not result.ok:
        return result.message
    return None


def ensure_default_hp(session, agent, *, default_hp: int | None = None) -> dict[str, Any]:
    """Seed HP/max_hp to default when missing. Returns current hp block."""
    default = state.DEFAULT_HP if default_hp is None else int(default_hp)
    block = get_hp_block(agent)
    if block.get("parse_error"):
        return block
    if block.get("initialized") and block.get("hp") is not None:
        max_hp = block.get("max_hp")
        if max_hp is None:
            max_hp = max(int(block["hp"]), default)
            write_hp(session, agent, hp=int(block["hp"]), max_hp=max_hp)
            return get_hp_block(agent)
        return block
    write_hp(session, agent, hp=default, max_hp=default)
    return get_hp_block(agent)
