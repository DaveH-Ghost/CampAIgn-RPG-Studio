"""Equip / unequip weapons and armor."""

from __future__ import annotations

import sys
from typing import Any

from campaign_rpg_engine.action_outcome import ActionOutcome

state = sys.modules["studio_plugin_combat.state"]
sheet = sys.modules["studio_plugin_combat.sheet"]

_EQUIP_VERB = "equip"
_UNEQUIP_VERB = "unequip"


def _inventory_mod():
    return sys.modules.get("studio_plugin_inventory.state")


def _skills_sheet(agent) -> dict[str, Any]:
    skills_sheet = sys.modules.get("studio_plugin_skills.sheet")
    skills_dice = sys.modules.get("studio_plugin_skills.dice")
    if skills_sheet is not None:
        return skills_sheet.get_sheet(agent)
    if skills_dice is not None:
        return {"stats": skills_dice.normalize_stats(None), "skills": {}}
    return {
        "stats": {"CON": 10, "STR": 10, "DEX": 10, "WIS": 10, "INT": 10, "CHM": 10},
        "skills": {},
    }


def _find_carried_item(session, agent_id: str, item_id: str) -> dict[str, Any] | None:
    inv = _inventory_mod()
    if inv is None:
        return None
    items, index = inv.find_item(session, agent_id, item_id)
    if index is None:
        return None
    return items[index]


def clear_stale_equipment(session, agent_id: str) -> None:
    """Unequip slots whose items are no longer carried."""
    inv = _inventory_mod()
    if inv is None:
        return
    weapon_id = state.get_equipped_weapon_id(session, agent_id)
    if weapon_id and _find_carried_item(session, agent_id, weapon_id) is None:
        state.set_equipped_weapon(session, agent_id, None)
    armor_id = state.get_equipped_armor_id(session, agent_id)
    if armor_id and _find_carried_item(session, agent_id, armor_id) is None:
        state.set_equipped_armor(session, agent_id, None)


def get_equipped_weapon(session, agent) -> dict[str, Any] | None:
    clear_stale_equipment(session, agent.id)
    item_id = state.get_equipped_weapon_id(session, agent.id)
    if not item_id:
        return None
    item = _find_carried_item(session, agent.id, item_id)
    if item is None:
        return None
    combat = sheet.parse_item_combat(item)
    if combat is None or combat.get("slot") != sheet.WEAPON_SLOT:
        return None
    return {**combat, "item_id": item_id, "name": str(item.get("name") or item_id)}


def get_equipped_armor(session, agent) -> dict[str, Any] | None:
    clear_stale_equipment(session, agent.id)
    item_id = state.get_equipped_armor_id(session, agent.id)
    if not item_id:
        return None
    item = _find_carried_item(session, agent.id, item_id)
    if item is None:
        return None
    combat = sheet.parse_item_combat(item)
    if combat is None or combat.get("slot") != sheet.ARMOR_SLOT:
        return None
    return {**combat, "item_id": item_id, "name": str(item.get("name") or item_id)}


def compute_ac(session, agent) -> int:
    skills = _skills_sheet(agent)
    stats = skills.get("stats") or {}
    dex = int(stats.get("DEX", 10))
    skills_dice = sys.modules.get("studio_plugin_skills.dice")
    if skills_dice is not None:
        dex_mod = skills_dice.stat_modifier(dex)
    else:
        dex_mod = (dex - 10) // 2

    armor = get_equipped_armor(session, agent)
    if armor is None:
        return 10 + dex_mod

    total = int(armor.get("base_ac", 10))
    ac_stat = armor.get("ac_stat")
    if ac_stat:
        score = int(stats.get(ac_stat, 10))
        if skills_dice is not None:
            mod = skills_dice.stat_modifier(score)
        else:
            mod = (score - 10) // 2
        cap = armor.get("ac_stat_cap")
        if cap is not None:
            mod = min(mod, int(cap))
        total += mod
    return total


def _check_req(agent, req: dict[str, int]) -> str | None:
    if not req:
        return None
    stats = _skills_sheet(agent).get("stats") or {}
    missing = []
    for stat, need in req.items():
        have = int(stats.get(stat, 10))
        if have < need:
            missing.append(f"{stat} {have} (need {need})")
    if missing:
        return "You do not meet the requirements: " + ", ".join(missing) + "."
    return None


def equip_item(session, agent, item_id: str) -> ActionOutcome | str:
    if not state.plugin_enabled(session):
        return "Combat plugin is not enabled."
    inv = _inventory_mod()
    if inv is None or not inv.plugin_enabled(session):
        return "Inventory plugin must be enabled to equip items."

    item_id = (item_id or "").strip()
    if not item_id:
        return "ERR:INVALID_TARGET: equip requires target item id"

    item = _find_carried_item(session, agent.id, item_id)
    if item is None:
        return f"You are not carrying {item_id!r}."

    combat = sheet.parse_item_combat(item)
    if combat is None:
        return f"{item.get('name') or item_id} is not a weapon or armor (missing combat_plugin)."

    req_err = _check_req(agent, combat.get("req") or {})
    if req_err:
        return req_err

    name = str(item.get("name") or item_id)
    clear_stale_equipment(session, agent.id)
    if combat["slot"] == sheet.WEAPON_SLOT:
        state.set_equipped_weapon(session, agent.id, item_id)
        attack_mod = sys.modules.get("studio_plugin_combat.attack")
        handlers = sys.modules.get("studio_plugin_combat.handlers")
        if attack_mod is not None and attack_mod._ATTACK_CTX is not None:
            verbs: list[str] = []
            if handlers is not None:
                verbs = handlers.weapon_attack_verbs(item, combat)
            elif combat.get("action"):
                verbs = [str(combat["action"])]
            for verb in verbs:
                attack_mod.ensure_attack_verb(attack_mod._ATTACK_CTX, verb)
        return ActionOutcome(
            result=f"You equip {name}.",
            passive_result=f"{agent.name} equips {name}.",
        )
    state.set_equipped_armor(session, agent.id, item_id)
    return ActionOutcome(
        result=f"You don {name}.",
        passive_result=f"{agent.name} dons {name}.",
    )


def unequip_item(session, agent, target: str) -> ActionOutcome | str:
    if not state.plugin_enabled(session):
        return "Combat plugin is not enabled."

    raw = (target or "").strip().lower()
    if not raw:
        return "ERR:INVALID_TARGET: unequip requires item id, 'weapon', or 'armor'"

    clear_stale_equipment(session, agent.id)
    weapon_id = state.get_equipped_weapon_id(session, agent.id)
    armor_id = state.get_equipped_armor_id(session, agent.id)

    if raw in ("weapon", "weapons"):
        if not weapon_id:
            return "You have no weapon equipped."
        state.set_equipped_weapon(session, agent.id, None)
        return ActionOutcome(
            result="You unequip your weapon.",
            passive_result=f"{agent.name} unequips a weapon.",
        )
    if raw in ("armor", "armour"):
        if not armor_id:
            return "You have no armor equipped."
        state.set_equipped_armor(session, agent.id, None)
        return ActionOutcome(
            result="You remove your armor.",
            passive_result=f"{agent.name} removes armor.",
        )

    item_id = (target or "").strip()
    if weapon_id == item_id:
        state.set_equipped_weapon(session, agent.id, None)
        return ActionOutcome(
            result="You unequip your weapon.",
            passive_result=f"{agent.name} unequips a weapon.",
        )
    if armor_id == item_id:
        state.set_equipped_armor(session, agent.id, None)
        return ActionOutcome(
            result="You remove your armor.",
            passive_result=f"{agent.name} removes armor.",
        )
    return f"{item_id!r} is not currently equipped."


def validate_equip_turn(turn) -> str | None:
    if not (turn.target or "").strip():
        return "ERR:INVALID_TARGET: equip requires target item id"
    return None


def validate_unequip_turn(turn) -> str | None:
    if not (turn.target or "").strip():
        return "ERR:INVALID_TARGET: unequip requires item id, 'weapon', or 'armor'"
    return None


def equip_turn_verb(session, agent, area, turn):
    del area
    return equip_item(session, agent, turn.target or "")


def unequip_turn_verb(session, agent, area, turn):
    del area
    return unequip_item(session, agent, turn.target or "")
