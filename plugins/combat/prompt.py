"""Combat prompt slot text."""

from __future__ import annotations

import sys

state = sys.modules["studio_plugin_combat.state"]
sheet = sys.modules["studio_plugin_combat.sheet"]
equip = sys.modules["studio_plugin_combat.equip"]
attack = sys.modules["studio_plugin_combat.attack"]


def format_combat_prompt(session, agent) -> str:
    if not state.plugin_enabled(session):
        return ""

    equip.clear_stale_equipment(session, agent.id)
    block = sheet.get_hp_block(agent)
    if state.combat_active(session):
        sheet.ensure_default_hp(session, agent)
        block = sheet.get_hp_block(agent)

    hp = block.get("hp")
    max_hp = block.get("max_hp")
    if hp is None:
        hp_line = f"HP: (not set; defaults to {state.DEFAULT_HP} when combat starts)"
    else:
        max_part = f"/{max_hp}" if max_hp is not None else ""
        hp_line = f"HP: {hp}{max_part}"

    ac = equip.compute_ac(session, agent)
    lines = [
        "Combat:",
        f"- {hp_line}",
        f"- AC: {ac}",
    ]

    weapon = equip.get_equipped_weapon(session, agent)
    armor = equip.get_equipped_armor(session, agent)
    if weapon:
        item_id = weapon.get("item_id")
        verbs: list[str] = []
        handlers = sys.modules.get("studio_plugin_combat.handlers")
        inv = sys.modules.get("studio_plugin_inventory.state")
        item = None
        if inv is not None and item_id:
            items, index = inv.find_item(session, agent.id, str(item_id))
            if index is not None:
                item = items[index]
        if handlers is not None:
            verbs = handlers.weapon_attack_verbs(item, weapon)
        elif weapon.get("action"):
            verbs = [str(weapon["action"])]
        verb_part = f" [{', '.join(verbs)}]" if verbs else " (add combat_attack Manage actions)"
        lines.append(
            f"- Equipped weapon: {weapon.get('name')} ({item_id}){verb_part}"
        )
    else:
        lines.append("- Equipped weapon: (none)")
    if armor:
        lines.append(f"- Equipped armor: {armor.get('name')} ({armor.get('item_id')})")
    else:
        lines.append("- Equipped armor: (none)")

    lines.extend(
        [
            "",
            'Equip anytime: "action": "verb", "verb": "equip", "target": "<item_id>".',
            'Unequip: "verb": "unequip", "target": "<item_id>" or "weapon" / "armor".',
        ]
    )

    if not state.combat_active(session):
        lines.extend(
            [
                "",
                "You are currently not in combat.",
                "Do not use attack verbs (weapon actions or unarmed) until combat starts.",
                "You may still equip or unequip gear.",
            ]
        )
        return "\n".join(lines)

    from backend.initiative import get_initiative_state

    init = get_initiative_state(session)
    order = list(init.get("order") or [])
    current_id = None
    try:
        idx = int(init.get("index") or 0)
        if 0 <= idx < len(order):
            current_id = order[idx]
    except (TypeError, ValueError):
        current_id = None

    lines.extend(["", "Combatants (initiative order — only these agents may be attacked):"])
    if not order:
        lines.append("- (none)")
    else:
        for aid in order:
            other = session.get_agent(aid)
            if other is None:
                lines.append(f"- {aid} (missing)")
                continue
            other_block = sheet.get_hp_block(other)
            ohp = other_block.get("hp")
            omax = other_block.get("max_hp")
            if ohp is None:
                hp_part = "HP ?"
            else:
                hp_part = f"HP {ohp}" + (f"/{omax}" if omax is not None else "")
            tags: list[str] = []
            if other.id == agent.id:
                tags.append("you")
            if other.id == current_id:
                tags.append("current turn")
            tag_part = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"- {other.name} ({other.id}) {hp_part}{tag_part}")

    profile = attack.attack_profile_for_agent(session, agent)
    verbs = attack.weapon_verbs_for_agent(session, agent)
    if attack._ATTACK_CTX is not None:
        for verb in verbs:
            attack.ensure_attack_verb(attack._ATTACK_CTX, verb)

    lines.extend(
        [
            "",
            "Combat is active. Attack actions:",
        ]
    )
    if not verbs:
        lines.append(
            "- (none — add Manage actions with handler combat_attack on the equipped weapon)"
        )
    else:
        stats_bit = (
            f"range {profile.get('range')}, "
            f"{profile.get('attack_stat')} +{profile.get('accuracy_bonus', 0)} accuracy, "
            f"damage {profile.get('damage')}"
            + (f" ({profile.get('name')})" if profile.get("name") else "")
        )
        for verb in verbs:
            lines.append(f"- {verb}: {stats_bit}")
        example = verbs[0]
        example_target = next(
            (aid for aid in order if aid != agent.id and session.get_agent(aid) is not None),
            "agent_goblin",
        )
        lines.append(
            f'Example: "action": "verb", "verb": "{example}", '
            f'"target": "{example_target}" '
            "(path into range unless your move already reaches)."
        )
    return "\n".join(lines)
