"""Attack resolution, combat start/end, and downed handling."""

from __future__ import annotations

import random
import sys
from typing import Any

from campaign_rpg_engine.action_outcome import ActionOutcome
from campaign_rpg_engine.grid import chebyshev_distance

state = sys.modules["studio_plugin_combat.state"]
sheet = sys.modules["studio_plugin_combat.sheet"]
dice = sys.modules["studio_plugin_combat.dice"]
equip = sys.modules["studio_plugin_combat.equip"]

_REGISTERED_ATTACK_VERBS: set[str] = set()
_ATTACK_CTX = None
# Queued [Downed] narrator lines; flushed after the turn increments session_turn
# so history order is attack first, then downed (same session_turn as the attack).
_deferred_downed_events: list[tuple[int, str]] = []


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


def _stat_mod(stats: dict[str, int], stat: str) -> int:
    skills_dice = sys.modules.get("studio_plugin_skills.dice")
    score = int(stats.get(stat, 10))
    if skills_dice is not None:
        return skills_dice.stat_modifier(score)
    return (score - 10) // 2


def agent_in_initiative(session, agent_id: str) -> bool:
    from backend.initiative import get_initiative_state, initiative_enabled

    if not initiative_enabled(session):
        return False
    order = get_initiative_state(session).get("order") or []
    return agent_id in order


def can_attack(session, agent_id: str) -> str | None:
    """Return an error message if *agent_id* cannot attack, else None."""
    if not state.plugin_enabled(session):
        return "Combat plugin is not enabled."
    if not state.combat_active(session):
        return "You cannot attack outside of combat."
    if not agent_in_initiative(session, agent_id):
        return "You are not in the initiative order."
    return None


def can_be_attacked(session, target) -> str | None:
    """Return an error if *target* is not a valid combat attack target."""
    if target is None:
        return "No target."
    block = sheet.get_hp_block(target)
    hp = block.get("hp")
    if hp is not None and int(hp) <= 0:
        return f"{target.name} is downed and cannot be attacked."
    if not agent_in_initiative(session, target.id):
        return f"{target.name} is not in the fight."
    return None


def attackable_agents_in_area(session, agent, area) -> list:
    """Other agents in *area* who are valid attack targets right now."""
    if area is None:
        return []
    out = []
    for other in area.agents:
        if other.id == agent.id:
            continue
        if can_be_attacked(session, other) is None:
            out.append(other)
    return out


def attack_profile_for_agent(session, agent) -> dict[str, Any]:
    weapon = equip.get_equipped_weapon(session, agent)
    if weapon is not None:
        return weapon
    return sheet.unarmed_profile()


def _equipped_weapon_item(session, agent) -> dict[str, Any] | None:
    profile = attack_profile_for_agent(session, agent)
    item_id = profile.get("item_id")
    if not item_id:
        return None
    inv = sys.modules.get("studio_plugin_inventory.state")
    if inv is None:
        return None
    items, index = inv.find_item(session, agent.id, str(item_id))
    if index is None:
        return None
    return items[index]


def weapon_verbs_for_agent(session, agent) -> list[str]:
    """Allowed attack verb names for the agent's current weapon (or unarmed)."""
    if equip.get_equipped_weapon(session, agent) is None:
        return [sheet.UNARMED_ACTION]
    handlers = sys.modules.get("studio_plugin_combat.handlers")
    item = _equipped_weapon_item(session, agent)
    profile = attack_profile_for_agent(session, agent)
    if handlers is None:
        if profile.get("action"):
            return [str(profile["action"])]
        return []
    return handlers.weapon_attack_verbs(item, profile)


def ensure_attack_verb(ctx, action_name: str) -> None:
    global _ATTACK_CTX
    _ATTACK_CTX = ctx
    name = (action_name or "").strip()
    if not name:
        return
    if name in (equip._EQUIP_VERB, equip._UNEQUIP_VERB):
        return
    _REGISTERED_ATTACK_VERBS.add(name)

    def validate_turn(turn):
        target = (turn.target or "").strip()
        if not target:
            return f"ERR:INVALID_TARGET: {name} requires target agent id"
        if not target.startswith("agent_"):
            return f"ERR:INVALID_TARGET: {name} target must be an agent id (agent_*)"
        return None

    def path_target(turn):
        return (turn.target or "").strip() or None

    def path_range(session, agent, area, turn):
        del area, turn
        profile = attack_profile_for_agent(session, agent)
        if name == sheet.UNARMED_ACTION and equip.get_equipped_weapon(session, agent):
            return sheet.UNARMED_RANGE
        if profile.get("action") == name or (
            name == sheet.UNARMED_ACTION and profile.get("item_id") is None
        ):
            return int(profile.get("range", 1))
        return int(profile.get("range", 1))

    def executor(session, agent, area, turn):
        return resolve_attack(
            session,
            agent,
            area,
            target_id=(turn.target or "").strip(),
            action_name=name,
        )

    # Always re-register: engine clear_turn_verbs_for_tests wipes the registry but
    # this module-level set survives across create_app() reloads in tests.
    ctx.register_turn_verb(
        name,
        executor,
        description=f"Combat attack action {name!r}",
        validate_turn=validate_turn,
        path_target_from_turn=path_target,
        path_range_from_turn=path_range,
    )


def register_known_attack_verbs(ctx, session=None) -> None:
    ensure_attack_verb(ctx, sheet.UNARMED_ACTION)
    if session is None:
        return
    inv = sys.modules.get("studio_plugin_inventory.state")
    if inv is None:
        return
    handlers = sys.modules.get("studio_plugin_combat.handlers")
    serialization = sys.modules.get("studio_plugin_inventory.serialization")
    ext = inv.ensure_inventory_state(session)
    for agent_id, items in (ext.get("by_agent") or {}).items():
        del agent_id
        if not isinstance(items, list):
            continue
        for item in items:
            combat = sheet.parse_item_combat(item)
            if combat and combat.get("slot") == sheet.WEAPON_SLOT:
                for verb in (
                    handlers.weapon_attack_verbs(item, combat)
                    if handlers is not None
                    else ([str(combat["action"])] if combat.get("action") else [])
                ):
                    ensure_attack_verb(ctx, verb)
            if handlers is None or serialization is None:
                continue
            actions = serialization.deserialize_actions(item.get("actions"))
            for name, action in actions.items():
                if getattr(action, "handler_id", None) == handlers.HANDLER_ID:
                    ensure_attack_verb(ctx, str(name))


def start_combat(session) -> dict[str, Any]:
    from backend.initiative import get_initiative_state, initiative_enabled

    if not state.plugin_enabled(session):
        return {"ok": False, "message": "Combat plugin is not enabled."}
    if not initiative_enabled(session):
        return {
            "ok": False,
            "message": "Enable initiative with a non-empty order before starting combat.",
        }
    init = get_initiative_state(session)
    order = list(init.get("order") or [])
    if not order:
        return {
            "ok": False,
            "message": "Initiative order is empty; add combatants before starting combat.",
        }

    seeded = []
    for agent_id in order:
        agent = session.get_agent(agent_id)
        if agent is None:
            continue
        before = sheet.get_hp_block(agent)
        sheet.ensure_default_hp(session, agent)
        if not before.get("initialized"):
            seeded.append(agent.name)

    state.set_combat_active(session, True)
    if _ATTACK_CTX is not None:
        register_known_attack_verbs(_ATTACK_CTX, session)

    names = ", ".join(
        session.get_agent(aid).name if session.get_agent(aid) else aid for aid in order
    )
    seed_note = f" Seeded HP {state.DEFAULT_HP} for: {', '.join(seeded)}." if seeded else ""
    text = f"[Combat Start] Combat begins! Initiative: {names}.{seed_note}"
    emit = session.emit_area_event(text.strip())
    if not emit.ok:
        return {"ok": False, "message": emit.message}
    return {"ok": True, "message": emit.message}


def end_combat(session) -> dict[str, Any]:
    if not state.plugin_enabled(session):
        return {"ok": False, "message": "Combat plugin is not enabled."}
    state.set_combat_active(session, False)
    emit = session.emit_area_event("[Combat End] Combat is over.")
    if not emit.ok:
        return {"ok": False, "message": emit.message}
    return {"ok": True, "message": emit.message}


def handle_area_event(session, **payload) -> None:
    if not state.plugin_enabled(session):
        return
    text = str(payload.get("text") or "").strip()
    upper = text.upper()
    if upper.startswith("[COMBAT START]"):
        # Avoid re-entrant emit loops: start_combat emits again.
        # Only toggle when inactive and skip if this event already came from start_combat.
        if state.combat_active(session):
            return
        # Strip tag and treat as start request without double-emitting the same text.
        _start_combat_quiet(session)
    elif upper.startswith("[COMBAT END]"):
        if not state.combat_active(session):
            return
        state.set_combat_active(session, False)


def _start_combat_quiet(session) -> dict[str, Any]:
    """Start combat without emitting another area event (listener path)."""
    from backend.initiative import get_initiative_state, initiative_enabled

    if not initiative_enabled(session):
        return {
            "ok": False,
            "message": "Enable initiative with a non-empty order before starting combat.",
        }
    order = list(get_initiative_state(session).get("order") or [])
    if not order:
        return {"ok": False, "message": "Initiative order is empty."}
    for agent_id in order:
        agent = session.get_agent(agent_id)
        if agent is not None:
            sheet.ensure_default_hp(session, agent)
    state.set_combat_active(session, True)
    if _ATTACK_CTX is not None:
        register_known_attack_verbs(_ATTACK_CTX, session)
    return {"ok": True, "message": "Combat started."}


def _apply_damage_and_maybe_down(
    session,
    attacker,
    target,
    damage_total: int,
) -> tuple[int, bool]:
    sheet.ensure_default_hp(session, target)
    block = sheet.get_hp_block(target)
    hp = int(block.get("hp") or 0)
    max_hp = int(block.get("max_hp") or state.DEFAULT_HP)
    new_hp = max(0, hp - damage_total)
    sheet.write_hp(session, target, hp=new_hp, max_hp=max_hp)
    if new_hp > 0:
        return new_hp, False

    from backend.initiative import remove_agent

    already_down = hp <= 0
    remove_agent(session, target.id)
    # Defer [Downed] area events until after the turn increments session_turn.
    # Emitting mid-verb uses the previous turn number and sorts before the attack.
    if not already_down:
        _deferred_downed_events.append(
            (
                id(session),
                (
                    f"[Downed] {target.name} is downed by {attacker.name} "
                    "and leaves the fight."
                ),
            )
        )
    return new_hp, True


def flush_deferred_downed_events(session) -> None:
    """Emit queued downed narrator lines (call after a successful turn)."""
    global _deferred_downed_events
    if not _deferred_downed_events:
        return
    sid = id(session)
    remaining: list[tuple[int, str]] = []
    for queued_sid, text in _deferred_downed_events:
        if queued_sid != sid:
            remaining.append((queued_sid, text))
            continue
        session.emit_area_event(text)
    _deferred_downed_events = remaining


def resolve_attack(
    session,
    agent,
    area,
    *,
    target_id: str,
    action_name: str,
    rng: random.Random | None = None,
) -> ActionOutcome | str:
    gate = can_attack(session, agent.id)
    if gate:
        return gate

    target_id = (target_id or "").strip()
    target = area.get_agent_by_id(target_id) if area is not None else None
    if target is None and session is not None:
        target = session.get_agent(target_id)
    if target is None:
        return f"Agent {target_id!r} not found."
    if target.id == agent.id:
        return "You cannot attack yourself."

    agent_area = session.get_area_for_agent(agent) if session is not None else area
    target_area = session.get_area_for_agent(target) if session is not None else area
    if agent_area is None or target_area is None or agent_area is not target_area:
        return f"{target.name} is not in your area."

    target_gate = can_be_attacked(session, target)
    if target_gate:
        return target_gate

    profile = attack_profile_for_agent(session, agent)
    if action_name == sheet.UNARMED_ACTION:
        if equip.get_equipped_weapon(session, agent) is not None:
            return "You have a weapon equipped; use its attack action instead of unarmed."
        profile = sheet.unarmed_profile()
    else:
        allowed = weapon_verbs_for_agent(session, agent)
        if action_name not in allowed:
            if not allowed:
                return (
                    "Equipped weapon has no attack actions. "
                    "Add Manage actions with handler combat_attack (e.g. swing, shoot)."
                )
            listed = ", ".join(repr(v) for v in allowed)
            return (
                f"You cannot use '{action_name}' right now "
                f"(equipped weapon attacks: {listed})."
            )

    action_range = int(profile.get("range", 1))
    dist = chebyshev_distance(agent.position, target.position)
    if dist > action_range:
        return (
            f"Unfortunately you are too far from {target.name} to {action_name} "
            f"(range {action_range}, distance {dist})."
        )

    sheet.ensure_default_hp(session, agent)
    sheet.ensure_default_hp(session, target)

    stats = _skills_sheet(agent).get("stats") or {}
    attack_stat = str(profile.get("attack_stat") or "STR")
    mod = _stat_mod(stats, attack_stat)
    accuracy = int(profile.get("accuracy_bonus") or 0)
    d20 = dice.roll_d20(rng=rng)
    total = d20 + mod + accuracy
    ac = equip.compute_ac(session, target)
    hit = total >= ac
    roll_detail = f"d20={d20}+{attack_stat}{mod:+d}"
    if accuracy:
        roll_detail += f"+weapon{accuracy:+d}"
    roll_detail += f"={total} vs AC {ac}"

    weapon_name = profile.get("name") or action_name
    attack_bonus = mod + accuracy
    handlers = sys.modules.get("studio_plugin_combat.handlers")

    combat_action = None
    if handlers is not None and action_name != sheet.UNARMED_ACTION:
        inv = sys.modules.get("studio_plugin_inventory.state")
        item = None
        item_id = profile.get("item_id")
        if inv is not None and item_id:
            items, index = inv.find_item(session, agent.id, str(item_id))
            if index is not None:
                item = items[index]
        combat_action = handlers.find_combat_attack_action(item, action_name)

    if not hit:
        if combat_action is not None and handlers is not None:
            return handlers.format_attack_outcome(
                action=combat_action,
                actor_name=agent.name,
                target_name=target.name,
                action_name=action_name,
                weapon_name=str(weapon_name),
                hit=False,
                attack_roll=d20,
                attack_bonus=attack_bonus,
                attack_total=total,
                target_ac=ac,
                attack_detail=roll_detail,
            )
        return ActionOutcome(
            result=f"You miss {target.name} with {action_name} ({roll_detail}).",
            passive_result=f"{agent.name} misses {target.name}.",
        )

    dmg = dice.roll_damage(str(profile.get("damage") or "1d4"), rng=rng)
    if isinstance(dmg, str):
        return dmg
    new_hp, downed = _apply_damage_and_maybe_down(session, agent, target, int(dmg["total"]))
    if combat_action is not None and handlers is not None:
        return handlers.format_attack_outcome(
            action=combat_action,
            actor_name=agent.name,
            target_name=target.name,
            action_name=action_name,
            weapon_name=str(weapon_name),
            hit=True,
            attack_roll=d20,
            attack_bonus=attack_bonus,
            attack_total=total,
            target_ac=ac,
            attack_detail=roll_detail,
            damage_detail=str(dmg["detail"]),
            damage_total=int(dmg["total"]),
            target_hp=new_hp,
            downed=downed,
        )
    down_note = f" {target.name} is downed!" if downed else f" ({target.name} HP {new_hp})."
    return ActionOutcome(
        result=(
            f"You hit {target.name} with {action_name} ({roll_detail}); "
            f"damage {dmg['detail']}.{down_note}"
        ),
        passive_result=(
            f"{agent.name} hits {target.name} with {weapon_name} "
            f"for {dmg['total']} damage."
            + (" They fall!" if downed else "")
        ),
    )
