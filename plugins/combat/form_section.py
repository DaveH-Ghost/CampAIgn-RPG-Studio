"""Object create/edit form section for combat weapon/armor private_data."""

from __future__ import annotations

import sys
from typing import Any

state = sys.modules["studio_plugin_combat.state"]
sheet = sys.modules["studio_plugin_combat.sheet"]

SECTION_ID = "equipment"
STAT_OPTIONS = [
    {"value": "STR", "label": "STR"},
    {"value": "DEX", "label": "DEX"},
    {"value": "CON", "label": "CON"},
    {"value": "WIS", "label": "WIS"},
    {"value": "INT", "label": "INT"},
    {"value": "CHM", "label": "CHM"},
]


def _req_str(req: dict[str, int] | None) -> str:
    if not req:
        return ""
    parts = [f"{k}:{v}" for k, v in sorted(req.items())]
    return ", ".join(parts)


def _parse_req(raw: Any) -> dict[str, int]:
    text = str(raw or "").strip()
    if not text:
        return {}
    out: dict[str, int] = {}
    for part in text.replace(";", ",").split(","):
        piece = part.strip()
        if not piece:
            continue
        if ":" in piece:
            name, value = piece.split(":", 1)
        elif "=" in piece:
            name, value = piece.split("=", 1)
        else:
            continue
        key = name.strip().upper()
        if not key:
            continue
        try:
            out[key] = int(value.strip())
        except (TypeError, ValueError):
            continue
    return out


def _current_block(entity) -> dict[str, Any] | None:
    if entity is None:
        return None
    item = {
        "private_data": getattr(entity, "private_data", "") or "",
    }
    return sheet.parse_item_combat(item)


def build_equipment_section(session, entity) -> dict[str, Any]:
    del session
    block = _current_block(entity)
    kind = "none"
    if block and block.get("slot") == sheet.WEAPON_SLOT:
        kind = "weapon"
    elif block and block.get("slot") == sheet.ARMOR_SLOT:
        kind = "armor"

    weapon = block if kind == "weapon" else {}
    armor = block if kind == "armor" else {}

    fields: list[dict[str, Any]] = [
        {
            "name": "kind",
            "label": "Combat role",
            "type": "select",
            "value": kind,
            "options": [
                {"value": "none", "label": "None (not equipment)"},
                {"value": "weapon", "label": "Weapon"},
                {"value": "armor", "label": "Armor"},
            ],
        },
        {
            "name": "range",
            "label": "Range (tiles)",
            "type": "number",
            "value": str(weapon.get("range", 1)),
            "showWhen": {"field": "kind", "values": ["weapon"]},
        },
        {
            "name": "attack_stat",
            "label": "Attack stat",
            "type": "select",
            "value": str(weapon.get("attack_stat") or "STR"),
            "options": STAT_OPTIONS,
            "showWhen": {"field": "kind", "values": ["weapon"]},
        },
        {
            "name": "accuracy_bonus",
            "label": "Accuracy bonus",
            "type": "number",
            "value": str(weapon.get("accuracy_bonus", 0)),
            "showWhen": {"field": "kind", "values": ["weapon"]},
        },
        {
            "name": "damage",
            "label": "Damage (NdM+mod)",
            "type": "text",
            "value": str(weapon.get("damage") or "1d8"),
            "showWhen": {"field": "kind", "values": ["weapon"]},
        },
        {
            "name": "weapon_req",
            "label": "Stat requirements (e.g. STR:12, DEX:10)",
            "type": "text",
            "value": _req_str(weapon.get("req") if isinstance(weapon, dict) else None),
            "showWhen": {"field": "kind", "values": ["weapon"]},
        },
        {
            "name": "base_ac",
            "label": "Base AC",
            "type": "number",
            "value": str(armor.get("base_ac", 14)),
            "showWhen": {"field": "kind", "values": ["armor"]},
        },
        {
            "name": "ac_stat",
            "label": "AC bonus stat (optional)",
            "type": "select",
            "value": str(armor.get("ac_stat") or ""),
            "options": [{"value": "", "label": "(none)"}] + STAT_OPTIONS,
            "showWhen": {"field": "kind", "values": ["armor"]},
        },
        {
            "name": "ac_stat_cap",
            "label": "AC stat bonus cap (optional)",
            "type": "number",
            "value": (
                ""
                if armor.get("ac_stat_cap") is None
                else str(armor.get("ac_stat_cap"))
            ),
            "showWhen": {"field": "kind", "values": ["armor"]},
        },
        {
            "name": "armor_req",
            "label": "Stat requirements (e.g. STR:10)",
            "type": "text",
            "value": _req_str(armor.get("req") if isinstance(armor, dict) else None),
            "showWhen": {"field": "kind", "values": ["armor"]},
        },
    ]
    return {
        "title": "Combat — weapon / armor",
        "fields": fields,
    }


def apply_equipment_values(
    existing: dict[str, Any] | None,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    del existing
    kind = str(values.get("kind") or "none").strip().lower()
    if kind in ("", "none"):
        return None
    if kind == "weapon":
        try:
            range_val = max(0, int(values.get("range") or 1))
        except (TypeError, ValueError):
            range_val = 1
        try:
            accuracy = int(values.get("accuracy_bonus") or 0)
        except (TypeError, ValueError):
            accuracy = 0
        attack_stat = str(values.get("attack_stat") or "STR").strip().upper() or "STR"
        damage = str(values.get("damage") or "1d4").strip() or "1d4"
        # Attack verb names live on Manage actions (combat_attack), not here.
        return {
            "slot": sheet.WEAPON_SLOT,
            "range": range_val,
            "attack_stat": attack_stat,
            "accuracy_bonus": accuracy,
            "damage": damage,
            "req": _parse_req(values.get("weapon_req")),
        }
    if kind == "armor":
        try:
            base_ac = int(values.get("base_ac") or 10)
        except (TypeError, ValueError):
            base_ac = 10
        ac_stat = str(values.get("ac_stat") or "").strip().upper() or None
        cap_raw = values.get("ac_stat_cap")
        ac_stat_cap: int | None
        if cap_raw is None or str(cap_raw).strip() == "":
            ac_stat_cap = None
        else:
            try:
                ac_stat_cap = int(cap_raw)
            except (TypeError, ValueError):
                ac_stat_cap = None
        block: dict[str, Any] = {
            "slot": sheet.ARMOR_SLOT,
            "base_ac": base_ac,
            "req": _parse_req(values.get("armor_req")),
        }
        if ac_stat:
            block["ac_stat"] = ac_stat
        if ac_stat_cap is not None:
            block["ac_stat_cap"] = ac_stat_cap
        return block
    return None
