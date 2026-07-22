"""Combat plugin — HP/AC, equip, and turn-based attacks (requires initiative)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_PLUGIN_DIR = Path(__file__).resolve().parent


def _import_plugin_module(relative_name: str):
    qualified = f"studio_plugin_combat.{relative_name}"
    if qualified in sys.modules:
        return sys.modules[qualified]
    path = _PLUGIN_DIR / f"{relative_name}.py"
    spec = importlib.util.spec_from_file_location(qualified, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load combat plugin module {relative_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


state = _import_plugin_module("state")
sheet = _import_plugin_module("sheet")
dice = _import_plugin_module("dice")
equip = _import_plugin_module("equip")
attack = _import_plugin_module("attack")
prompt = _import_plugin_module("prompt")
handlers = _import_plugin_module("handlers")
form_section = _import_plugin_module("form_section")

PLUGIN_ID = state.PLUGIN_ID
PLUGIN_LABEL = "Combat"
PLUGIN_VERSION = "1"
PLUGIN_DESCRIPTION = (
    "Turn-based combat with equippable weapons/armor, HP/AC, and attack verbs. "
    "Soft-requires Inventory + Skills. Start combat only with initiative enabled; "
    "place the combat prompt block below inventory. Unarmed: range 1, STR, 1d4. "
    "Mark weapons/armor under object Edit → Plugins (stats only); "
    "add Manage action combat_attack for each attack verb and hit/miss text."
)


def _prompt_slot(session, agent, area, ctx_prompt, options):
    del area, ctx_prompt, options
    return prompt.format_combat_prompt(session, agent)


def _build_panel(session):
    agent = session.get_active_agent()
    max_hp_value = "10"
    if agent is not None:
        block = sheet.get_hp_block(agent)
        if block.get("max_hp") is not None:
            max_hp_value = str(block["max_hp"])
        elif block.get("hp") is not None:
            max_hp_value = str(block["hp"])

    sections: list[dict[str, Any]] = [
        {
            "type": "text",
            "content": (
                "Combat uses initiative order as the fighter list. "
                "Start refuses if initiative is off or empty. "
                "Recommend a prompt layout block plugin_slot named combat below inventory. "
                "Weapon/armor stats: object Edit → Plugins. "
                "Attack verbs + hit/miss copy: Manage actions → handler combat_attack "
                "(one or more names, e.g. swing and shoot)."
            ),
        },
        {
            "type": "key_value_list",
            "items": [
                {
                    "key": "Combat active",
                    "value": "yes" if state.combat_active(session) else "no",
                },
            ],
        },
        {
            "type": "button",
            "id": "set_max_hp",
            "label": "Set max HP (fills current HP)",
            "inputs": [
                {
                    "id": "max_hp_input",
                    "type": "number",
                    "label": "Active agent max HP",
                    "value": max_hp_value,
                    "min": 1,
                },
            ],
            "params_from_inputs": {"max_hp": "max_hp_input"},
        },
        {
            "type": "button",
            "id": "start_combat",
            "label": "Start combat",
        },
        {
            "type": "button",
            "id": "end_combat",
            "label": "End combat",
        },
    ]

    if agent is not None:
        block = sheet.get_hp_block(agent)
        hp = block.get("hp")
        max_hp = block.get("max_hp")
        hp_text = "not set" if hp is None else f"{hp}" + (f"/{max_hp}" if max_hp else "")
        sections.insert(
            1,
            {
                "type": "key_value_list",
                "items": [
                    {"key": f"{agent.name} HP", "value": hp_text},
                    {"key": "AC", "value": str(equip.compute_ac(session, agent))},
                    {
                        "key": "Weapon",
                        "value": (
                            (equip.get_equipped_weapon(session, agent) or {}).get("name")
                            or "(none)"
                        ),
                    },
                    {
                        "key": "Armor",
                        "value": (
                            (equip.get_equipped_armor(session, agent) or {}).get("name")
                            or "(none)"
                        ),
                    },
                ],
            },
        )
        inv = sys.modules.get("studio_plugin_inventory.state")
        if inv is not None and inv.plugin_enabled(session):
            gear_rows: list[dict[str, Any]] = []
            for item in inv.agent_items(session, agent.id):
                item_id = str(item.get("item_id") or "").strip()
                if not item_id:
                    continue
                combat = sheet.parse_item_combat(item)
                if combat is None:
                    continue
                label = str(item.get("name") or item_id)
                slot = combat.get("slot")
                equipped = state.is_item_equipped(session, agent.id, item_id)
                mark = " [equipped]" if equipped else ""
                gear_rows.append(
                    {
                        "item_id": item_id,
                        "label": f"{label} ({slot}){mark}",
                        "equipped": equipped,
                    }
                )
            if gear_rows:
                sections.append(
                    {
                        "type": "text",
                        "content": (
                            f"GM equip for {agent.name} (set them active first). "
                            "Equip/unequip without spending a turn."
                        ),
                    }
                )
                for row in gear_rows:
                    if row["equipped"]:
                        sections.append(
                            {
                                "type": "button",
                                "id": "unequip_item",
                                "label": f"Unequip {row['label']}",
                                "params": {"item_id": row["item_id"]},
                            }
                        )
                    else:
                        sections.append(
                            {
                                "type": "button",
                                "id": "equip_item",
                                "label": f"Equip {row['label']}",
                                "params": {"item_id": row["item_id"]},
                            }
                        )
            else:
                sections.append(
                    {
                        "type": "text",
                        "content": (
                            f"{agent.name} has no combat gear in inventory. "
                            "Grant a weapon/armor template from the Inventory panel first."
                        ),
                    }
                )

    return {
        "title": "Combat",
        "description": PLUGIN_DESCRIPTION,
        "sections": sections,
    }


def _start_combat_action(session, params: dict[str, Any]) -> dict[str, Any]:
    del params
    return attack.start_combat(session)


def _end_combat_action(session, params: dict[str, Any]) -> dict[str, Any]:
    del params
    return attack.end_combat(session)


def _set_max_hp_action(session, params: dict[str, Any]) -> dict[str, Any]:
    if not state.plugin_enabled(session):
        return {"ok": False, "message": "Combat plugin is not enabled."}
    agent = session.get_active_agent()
    if agent is None:
        return {"ok": False, "message": "No active agent."}
    raw = params.get("max_hp", params.get("max_hp_input", ""))
    if raw is None or str(raw).strip() == "":
        raw = "10"
    try:
        max_hp = int(raw)
    except (TypeError, ValueError):
        return {"ok": False, "message": "max_hp must be an integer."}
    if max_hp < 1:
        return {"ok": False, "message": "max_hp must be at least 1."}
    err = sheet.write_hp(session, agent, hp=max_hp, max_hp=max_hp)
    if err:
        return {"ok": False, "message": err}
    return {
        "ok": True,
        "message": f"Set {agent.name} HP to {max_hp}/{max_hp}.",
    }


def _panel_outcome(result) -> dict[str, Any]:
    if isinstance(result, str):
        return {"ok": False, "message": result}
    from campaign_rpg_engine.action_outcome import ActionOutcome

    if isinstance(result, ActionOutcome):
        return {"ok": True, "message": result.result or "Done."}
    return {"ok": True, "message": str(result)}


def _equip_item_action(session, params: dict[str, Any]) -> dict[str, Any]:
    if not state.plugin_enabled(session):
        return {"ok": False, "message": "Combat plugin is not enabled."}
    agent = session.get_active_agent()
    if agent is None:
        return {"ok": False, "message": "No active agent — select the NPC first."}
    item_id = str(params.get("item_id") or "").strip()
    if not item_id:
        return {"ok": False, "message": "Missing item_id."}
    return _panel_outcome(equip.equip_item(session, agent, item_id))


def _unequip_item_action(session, params: dict[str, Any]) -> dict[str, Any]:
    if not state.plugin_enabled(session):
        return {"ok": False, "message": "Combat plugin is not enabled."}
    agent = session.get_active_agent()
    if agent is None:
        return {"ok": False, "message": "No active agent — select the NPC first."}
    item_id = str(params.get("item_id") or "").strip()
    if not item_id:
        return {"ok": False, "message": "Missing item_id."}
    return _panel_outcome(equip.unequip_item(session, agent, item_id))


def _player_turn_assist(session):
    if not state.plugin_enabled(session):
        return []
    agent_id = getattr(session, "active_agent_id", None)
    if not agent_id:
        return []
    agent = session.get_agent(agent_id)
    if agent is None:
        return []

    rows: list[dict[str, Any]] = []
    inv = sys.modules.get("studio_plugin_inventory.state")
    if inv is not None and inv.plugin_enabled(session):
        for item in inv.agent_items(session, agent_id):
            item_id = str(item.get("item_id") or "").strip()
            if not item_id:
                continue
            combat = sheet.parse_item_combat(item)
            if combat is None:
                continue
            label = str(item.get("name") or item_id)
            if state.is_item_equipped(session, agent_id, item_id):
                label = f"{label} [equipped]"
            rows.append(
                {
                    "id": item_id,
                    "label": label,
                    "verbs": [equip._EQUIP_VERB, equip._UNEQUIP_VERB],
                }
            )

    if state.combat_active(session) and attack.can_attack(session, agent_id) is None:
        verbs = attack.weapon_verbs_for_agent(session, agent)
        area = session.get_area_for_agent(agent)
        if area is not None and verbs:
            for other in attack.attackable_agents_in_area(session, agent, area):
                rows.append(
                    {
                        "id": other.id,
                        "label": f"Attack {other.name}",
                        "verbs": list(verbs),
                    }
                )
    return rows


def register(ctx):
    attack.ensure_attack_verb(ctx, sheet.UNARMED_ACTION)

    ctx.register_handler(
        handlers.HANDLER_ID,
        handlers.combat_attack_stub,
        description=(
            "Weapon attack narrative for combat turn verbs "
            "(hit = action result/passive; miss = miss_result/miss_passive params)"
        ),
        validate_params=handlers.validate_combat_attack_params,
        param_fields=handlers.PARAM_FIELDS,
        summary_template=handlers.SUMMARY_TEMPLATE,
    )
    ctx.register_interact_template_vars(list(handlers.INTERACT_TEMPLATE_VARS))
    ctx.register_entity_form_section(
        "object",
        form_section.SECTION_ID,
        form_section.build_equipment_section,
        private_key=state.PRIVATE_KEY,
        apply_values=form_section.apply_equipment_values,
    )

    ctx.register_turn_verb(
        equip._EQUIP_VERB,
        equip.equip_turn_verb,
        description="Equip a carried weapon or armor (target = item id)",
        validate_turn=equip.validate_equip_turn,
    )
    ctx.register_turn_verb(
        equip._UNEQUIP_VERB,
        equip.unequip_turn_verb,
        description="Unequip weapon/armor (target = item id, weapon, or armor)",
        validate_turn=equip.validate_unequip_turn,
    )

    ctx.register_prompt_slot(
        "combat",
        _prompt_slot,
        description="HP, AC, equipment, and combat attack actions",
    )
    ctx.register_player_turn_assist(_player_turn_assist)
    ctx.set_panel_builder(_build_panel)
    ctx.register_panel_action("start_combat", _start_combat_action)
    ctx.register_panel_action("end_combat", _end_combat_action)
    ctx.register_panel_action("set_max_hp", _set_max_hp_action)
    ctx.register_panel_action("equip_item", _equip_item_action)
    ctx.register_panel_action("unequip_item", _unequip_item_action)
    ctx.on("area_event", attack.handle_area_event)
    ctx.on("session_loaded", lambda session: attack.register_known_attack_verbs(ctx, session))
