"""combat_attack interaction handler — hit/miss narrative for weapon actions."""

from __future__ import annotations

import sys
from typing import Any

from campaign_rpg_engine.action_outcome import ActionOutcome

state = sys.modules["studio_plugin_combat.state"]

HANDLER_ID = "combat_attack"

PARAM_FIELDS = [
    {
        "name": "miss_result",
        "label": "Miss result (first person)",
        "type": "textarea",
        "required": False,
        "template_vars": True,
        "default": "You miss {target} with {action} ({attack_detail}).",
    },
    {
        "name": "miss_passive",
        "label": "Miss passive / area event",
        "type": "textarea",
        "required": False,
        "template_vars": True,
        "default": "{actor} misses {target}.",
    },
]

SUMMARY_TEMPLATE = "combat_attack"

INTERACT_TEMPLATE_VARS = (
    {
        "name": "attack_roll",
        "description": "Natural d20 attack roll (combat_attack / attack verbs)",
    },
    {
        "name": "attack_bonus",
        "description": "Signed total accuracy bonus (stat mod + weapon; combat)",
    },
    {
        "name": "attack_total",
        "description": "attack_roll + attack_bonus (combat)",
    },
    {
        "name": "target_ac",
        "description": "Target armor class this attack rolled against (combat)",
    },
    {
        "name": "attack_detail",
        "description": "Full accuracy breakdown string, e.g. d20=12+STR+1=13 vs AC 14 (combat)",
    },
    {
        "name": "damage_detail",
        "description": "Damage dice breakdown on a hit (combat)",
    },
    {
        "name": "damage_total",
        "description": "Total damage dealt on a hit (combat)",
    },
    {
        "name": "target_hp",
        "description": "Target HP remaining after this hit (combat)",
    },
    {
        "name": "target",
        "description": "Target agent name (combat)",
    },
    {
        "name": "action",
        "description": "Attack action name, e.g. swing (combat)",
    },
    {
        "name": "weapon",
        "description": "Weapon display name or Unarmed (combat)",
    },
)


def validate_combat_attack_params(params: dict[str, str]) -> str | None:
    del params
    return None


def combat_attack_stub(session, area, agent, obj, action) -> str | None:
    """
    Map/inventory interact stub.

    Combat resolution uses turn verbs; this handler exists so Manage actions can
    store miss templates and so the action editor shows combat placeholders.
    """
    del session, area, agent, obj, action
    return (
        "Use this weapon's attack as a turn verb against an agent "
        "(equip first, then verb = action name, target = agent id) while combat is active."
    )


def format_attack_outcome(
    *,
    action,
    actor_name: str,
    target_name: str,
    action_name: str,
    weapon_name: str,
    hit: bool,
    attack_roll: int,
    attack_bonus: int,
    attack_total: int,
    target_ac: int,
    attack_detail: str,
    damage_detail: str = "",
    damage_total: int = 0,
    target_hp: int | None = None,
    downed: bool = False,
) -> ActionOutcome:
    """Build ActionOutcome from action templates + combat roll vars."""
    params = dict(getattr(action, "handler_params", None) or {})
    extra = {
        "attack_roll": str(attack_roll),
        "attack_bonus": f"{attack_bonus:+d}",
        "attack_total": str(attack_total),
        "target_ac": str(target_ac),
        "attack_detail": attack_detail,
        "damage_detail": damage_detail,
        "damage_total": str(damage_total),
        "target_hp": "" if target_hp is None else str(target_hp),
        "target": target_name,
        "action": action_name,
        "weapon": weapon_name,
        "actor": actor_name,
        "object": weapon_name,
    }

    def _fmt(template: str, fallback: str) -> str:
        out = (template or "").strip() or fallback
        for key, value in extra.items():
            out = out.replace("{" + key + "}", value)
        return out

    if hit:
        result = _fmt(
            getattr(action, "result", "") or "",
            f"You hit {target_name} with {action_name} ({attack_detail})"
            + (f"; damage {damage_detail}." if damage_detail else "."),
        )
        passive = _fmt(
            getattr(action, "passive_result", "") or "",
            f"{actor_name} hits {target_name} with {weapon_name}"
            + (f" for {damage_total} damage." if damage_total else "."),
        )
        if downed and "down" not in result.lower():
            result = result.rstrip(".") + f" {target_name} is downed!"
        return ActionOutcome(result=result, passive_result=passive)

    miss_result = str(params.get("miss_result") or "")
    miss_passive = str(params.get("miss_passive") or "")
    return ActionOutcome(
        result=_fmt(
            miss_result,
            f"You miss {target_name} with {action_name} ({attack_detail}).",
        ),
        passive_result=_fmt(
            miss_passive,
            f"{actor_name} misses {target_name}.",
        ),
    )


def find_combat_attack_action(item: dict[str, Any] | None, action_name: str):
    """Return ObjectAction for *action_name* on *item* when handler is combat_attack."""
    if not item:
        return None
    serialization = sys.modules.get("studio_plugin_inventory.serialization")
    if serialization is None:
        return None
    actions = serialization.deserialize_actions(item.get("actions"))
    action = actions.get(action_name)
    if action is None:
        return None
    if action.handler_id != HANDLER_ID:
        return None
    return action


def combat_attack_action_names(item: dict[str, Any] | None) -> list[str]:
    """Manage-action names on *item* that use the combat_attack handler."""
    if not item:
        return []
    serialization = sys.modules.get("studio_plugin_inventory.serialization")
    if serialization is None:
        return []
    actions = serialization.deserialize_actions(item.get("actions"))
    names: list[str] = []
    for name, action in actions.items():
        if getattr(action, "handler_id", None) == HANDLER_ID:
            names.append(str(name))
    return names


def weapon_attack_verbs(item: dict[str, Any] | None, combat: dict[str, Any] | None) -> list[str]:
    """Turn verbs allowed for a weapon: Manage combat_attack names, else legacy action."""
    names = combat_attack_action_names(item)
    if names:
        return names
    if combat and combat.get("action"):
        return [str(combat["action"])]
    return []
