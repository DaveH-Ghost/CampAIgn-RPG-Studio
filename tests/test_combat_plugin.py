"""Combat plugin integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend.app import create_app
from backend.initiative import get_initiative_state, put_initiative, remove_agent
from backend.plugin_registry import clear_plugin_registry_for_tests
from backend.plugin_upload import load_all_plugins
from backend.session_store import reset_session_store
from campaign_rpg_engine import (
    ObjectAction,
    clear_event_listeners_for_tests,
    clear_turn_verbs_for_tests,
)
from campaign_rpg_engine.prompt_slots.registry import clear_prompt_slots_for_tests
from fastapi.testclient import TestClient
from reference_handlers import register_reference_handlers
from tests.world_helpers import (
    add_object_action,
    create_agent,
    create_object,
    get_session,
)

_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


@pytest.fixture(autouse=True)
def _fresh_combat_plugin_state():
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()
    register_reference_handlers()
    load_all_plugins(extra_dirs=[_PLUGINS_DIR])
    yield
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()


@pytest.fixture
def client():
    return TestClient(create_app())


def _enable_deps(client):
    assert client.post("/api/plugins/inventory/enable").json()["ok"] is True
    assert client.post("/api/plugins/skills/enable").json()["ok"] is True
    assert client.post("/api/plugins/combat/enable").json()["ok"] is True


def _weapon_private_data(**overrides):
    block = {
        "slot": "weapon",
        "action": "swing",
        "range": 1,
        "attack_stat": "STR",
        "accuracy_bonus": 5,
        "damage": "1d4+10",
        "req": {},
    }
    block.update(overrides)
    return json.dumps({"combat_plugin": block})


def _armor_private_data(**overrides):
    block = {
        "slot": "armor",
        "base_ac": 12,
        "ac_stat": "DEX",
        "ac_stat_cap": 2,
        "req": {},
    }
    block.update(overrides)
    return json.dumps({"combat_plugin": block})


def _give_item(session, agent_id: str, item: dict):
    inv = session.get_extension("inventory")
    if not isinstance(inv, dict):
        inv = {"by_agent": {}}
        session.set_extension("inventory", inv)
    by_agent = inv.setdefault("by_agent", {})
    items = list(by_agent.get(agent_id) or [])
    items.append(item)
    by_agent[agent_id] = items


def _setup_fighters(client):
    _enable_deps(client)
    fighter = create_agent(
        name="Fighter",
        position=(0, 0),
        personality="Brave.",
        is_player=True,
    )
    foe = create_agent(
        name="Foe",
        position=(1, 0),
        personality="Mean.",
        is_player=False,
    )
    session = get_session()
    put_initiative(session, enabled=True, order=[fighter.id, foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    return fighter, foe


def test_combat_plugin_in_catalog(client):
    response = client.get("/api/plugins")
    assert response.status_code == 200
    ids = {p["id"] for p in response.json()["plugins"]}
    assert "combat" in ids


def test_start_combat_refuses_without_initiative(client):
    _enable_deps(client)
    create_agent(name="Solo", position=(0, 0), personality="x")
    response = client.post(
        "/api/plugins/combat/action",
        json={"action_id": "start_combat", "params": {}},
    )
    assert response.status_code == 400
    detail = response.json().get("detail") or ""
    assert "initiative" in str(detail).lower()


def test_start_combat_seeds_hp_and_end_clears(client):
    fighter, foe = _setup_fighters(client)
    response = client.post(
        "/api/plugins/combat/action",
        json={"action_id": "start_combat", "params": {}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    session = get_session()
    assert session.get_extension("combat")["active"] is True
    for agent in (session.get_agent(fighter.id), session.get_agent(foe.id)):
        data = json.loads(agent.private_data)
        assert data["combat_plugin"]["hp"] == 10
        assert data["combat_plugin"]["max_hp"] == 10

    end = client.post(
        "/api/plugins/combat/action",
        json={"action_id": "end_combat", "params": {}},
    )
    assert end.json()["ok"] is True
    assert get_session().get_extension("combat")["active"] is False


def test_emit_combat_start_tag(client):
    fighter, foe = _setup_fighters(client)
    del foe
    session = get_session()
    import studio_plugin_combat.state as combat_state

    combat_state.ensure_combat_state(session)
    assert session.get_extension("combat").get("active") is not True
    result = session.emit_area_event("[Combat Start] Fight!")
    assert result.ok
    assert session.get_extension("combat")["active"] is True
    data = json.loads(session.get_agent(fighter.id).private_data)
    assert data["combat_plugin"]["hp"] == 10


def test_equip_unequip_and_inventory_equipped_marker(client):
    fighter, _foe = _setup_fighters(client)
    session = get_session()
    sword = {
        "item_id": "obj_sword_1",
        "name": "Longsword",
        "private_data": _weapon_private_data(req={"STR": 20}),
        "actions": {},
    }
    _give_item(session, fighter.id, sword)

    # Fail equip on unmet req
    bad = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Try equip.",
                "action": "verb",
                "verb": "equip",
                "target": "obj_sword_1",
            },
        },
    )
    assert bad.status_code == 200
    assert "requirement" in bad.json()["message"].lower() or "STR" in bad.json()["message"]

    sword["private_data"] = _weapon_private_data(req={})
    session.get_extension("inventory")["by_agent"][fighter.id] = [sword]
    put_initiative(session, enabled=True, order=[fighter.id, _foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})

    ok = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Equip.",
                "action": "verb",
                "verb": "equip",
                "target": "obj_sword_1",
            },
        },
    )
    assert ok.json()["ok"] is True
    assert session.get_extension("combat")["by_agent"][fighter.id]["equipped_weapon"] == (
        "obj_sword_1"
    )

    import studio_plugin_inventory as inv_plugin

    text = inv_plugin._format_inventory_prompt(session, fighter.id)
    assert "[equipped]" in text

    put_initiative(session, enabled=True, order=[fighter.id, _foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    unequip = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Unequip.",
                "action": "verb",
                "verb": "unequip",
                "target": "weapon",
            },
        },
    )
    assert unequip.json()["ok"] is True
    assert session.get_extension("combat")["by_agent"][fighter.id]["equipped_weapon"] is None


def test_drop_equipped_weapon_clears_combat_slot(client):
    fighter, _foe = _setup_fighters(client)
    session = get_session()
    sword = {
        "item_id": "obj_sword_drop",
        "name": "Droppable",
        "private_data": _weapon_private_data(req={}),
        "actions": {},
        "blocks_movement": False,
    }
    _give_item(session, fighter.id, sword)
    put_initiative(session, enabled=True, order=[fighter.id, _foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    assert (
        client.post(
            "/api/turn/manual",
            json={
                "compound_turn": {
                    "reasoning": "Equip.",
                    "action": "verb",
                    "verb": "equip",
                    "target": "obj_sword_drop",
                },
            },
        ).json()["ok"]
        is True
    )
    assert session.get_extension("combat")["by_agent"][fighter.id]["equipped_weapon"] == (
        "obj_sword_drop"
    )
    put_initiative(session, enabled=True, order=[fighter.id, _foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    drop = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Drop equipped.",
                "action": "verb",
                "verb": "drop",
                "target": "obj_sword_drop",
            },
        },
    )
    assert drop.json()["ok"] is True, drop.json()
    assert session.get_extension("combat")["by_agent"][fighter.id]["equipped_weapon"] is None


def test_attack_refused_outside_combat_unarmed_in_combat(client, monkeypatch):
    fighter, foe = _setup_fighters(client)
    session = get_session()

    refused = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Punch.",
                "action": "verb",
                "verb": "unarmed",
                "target": foe.id,
            },
        },
    )
    assert refused.json()["ok"] is True
    assert "outside of combat" in refused.json()["message"].lower()

    put_initiative(session, enabled=True, order=[fighter.id, foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    assert client.post(
        "/api/plugins/combat/action",
        json={"action_id": "start_combat", "params": {}},
    ).json()["ok"]

    import studio_plugin_combat.dice as combat_dice

    monkeypatch.setattr(combat_dice, "roll_d20", lambda rng=None: 15)
    monkeypatch.setattr(
        combat_dice,
        "roll_damage",
        lambda expr, rng=None: {
            "expr": expr,
            "rolls": [4],
            "modifier": 0,
            "total": 4,
            "detail": "1d4=4",
        },
    )

    hit = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Punch.",
                "action": "verb",
                "verb": "unarmed",
                "target": foe.id,
            },
        },
    )
    body = hit.json()
    assert body["ok"] is True
    assert "hit" in body["message"].lower() or "miss" in body["message"].lower()
    foe_agent = session.get_agent(foe.id)
    hp = json.loads(foe_agent.private_data)["combat_plugin"]["hp"]
    assert hp in (6, 10)  # hit → 6, miss → 10


def test_combat_prompt_lists_initiative_combatants(client):
    fighter, foe = _setup_fighters(client)
    session = get_session()
    assert client.post(
        "/api/plugins/combat/action",
        json={"action_id": "start_combat", "params": {}},
    ).json()["ok"]

    import studio_plugin_combat.prompt as combat_prompt

    text = combat_prompt.format_combat_prompt(session, session.get_agent(fighter.id))
    assert "Combatants (initiative order" in text
    assert f"Fighter ({fighter.id})" in text
    assert f"Foe ({foe.id})" in text
    assert "you" in text
    assert "current turn" in text


def test_downed_removes_from_initiative(client, monkeypatch):
    fighter, foe = _setup_fighters(client)
    session = get_session()
    assert client.post(
        "/api/plugins/combat/action",
        json={"action_id": "start_combat", "params": {}},
    ).json()["ok"]

    # Set foe to 1 HP
    foe_agent = session.get_agent(foe.id)
    session.set_entity_private_data(
        foe.id,
        json.dumps({"combat_plugin": {"hp": 1, "max_hp": 10}}),
    )

    import studio_plugin_combat.dice as combat_dice

    monkeypatch.setattr(combat_dice, "roll_d20", lambda rng=None: 20)
    monkeypatch.setattr(
        combat_dice,
        "roll_damage",
        lambda expr, rng=None: {
            "expr": expr,
            "rolls": [4],
            "modifier": 0,
            "total": 4,
            "detail": "1d4=4",
        },
    )

    hit = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Finish them.",
                "action": "verb",
                "verb": "unarmed",
                "target": foe.id,
            },
        },
    )
    assert hit.json()["ok"] is True
    order = get_initiative_state(session).get("order") or []
    assert foe.id not in order
    assert fighter.id in order
    assert json.loads(session.get_agent(foe.id).private_data)["combat_plugin"]["hp"] == 0

    # Already downed / off initiative — further attacks must fail (no damage / no re-down).
    put_initiative(session, enabled=True, order=[fighter.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    blocked = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Hit a corpse.",
                "action": "verb",
                "verb": "unarmed",
                "target": foe.id,
            },
        },
    )
    body = blocked.json()
    assert body["ok"] is True  # turn runs; verb returns an error string as result
    msg = (body.get("message") or "").lower()
    assert "downed" in msg or "not in the fight" in msg
    assert json.loads(session.get_agent(foe.id).private_data)["combat_plugin"]["hp"] == 0


def test_gm_panel_equip_active_agent(client):
    fighter, _foe = _setup_fighters(client)
    session = get_session()
    sword = {
        "item_id": "obj_gm_equip_sword",
        "name": "Spear",
        "private_data": _weapon_private_data(req={}),
        "actions": {},
    }
    _give_item(session, fighter.id, sword)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    equip_res = client.post(
        "/api/plugins/combat/action",
        json={"action_id": "equip_item", "params": {"item_id": "obj_gm_equip_sword"}},
    )
    assert equip_res.json()["ok"] is True, equip_res.json()
    assert session.get_extension("combat")["by_agent"][fighter.id]["equipped_weapon"] == (
        "obj_gm_equip_sword"
    )
    unequip_res = client.post(
        "/api/plugins/combat/action",
        json={"action_id": "unequip_item", "params": {"item_id": "obj_gm_equip_sword"}},
    )
    assert unequip_res.json()["ok"] is True
    assert session.get_extension("combat")["by_agent"][fighter.id]["equipped_weapon"] is None


def test_combat_prompt_says_not_in_combat_when_inactive(client):
    fighter, _foe = _setup_fighters(client)
    session = get_session()
    import studio_plugin_combat.prompt as combat_prompt

    text = combat_prompt.format_combat_prompt(session, session.get_agent(fighter.id))
    assert "You are currently not in combat" in text
    assert "Do not use attack verbs" in text


def test_remove_agent_repairs_index():
    session = get_session()
    a = create_agent(name="A", position=(0, 0), personality="x")
    b = create_agent(name="B", position=(1, 0), personality="x")
    c = create_agent(name="C", position=(2, 0), personality="x")
    put_initiative(session, enabled=True, order=[a.id, b.id, c.id], index=1)
    remove_agent(session, b.id)
    state = get_initiative_state(session)
    assert state["order"] == [a.id, c.id]
    assert state["index"] == 1
    assert state["order"][state["index"]] == c.id


def test_equip_armor_and_swing_attack(client, monkeypatch):
    fighter, foe = _setup_fighters(client)
    session = get_session()
    _give_item(
        session,
        fighter.id,
        {
            "item_id": "obj_sword_1",
            "name": "Longsword",
            "private_data": _weapon_private_data(accuracy_bonus=20, damage="1d4"),
            "actions": {},
        },
    )
    _give_item(
        session,
        foe.id,
        {
            "item_id": "obj_armor_1",
            "name": "Leather",
            "private_data": _armor_private_data(base_ac=30),
            "actions": {},
        },
    )
    import studio_plugin_combat.state as combat_state

    combat_state.set_equipped_armor(session, foe.id, "obj_armor_1")

    put_initiative(session, enabled=True, order=[fighter.id, foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    assert (
        client.post(
            "/api/turn/manual",
            json={
                "compound_turn": {
                    "reasoning": "Sword.",
                    "action": "verb",
                    "verb": "equip",
                    "target": "obj_sword_1",
                },
            },
        ).json()["ok"]
        is True
    )
    put_initiative(session, enabled=True, order=[fighter.id, foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})
    assert client.post(
        "/api/plugins/combat/action",
        json={"action_id": "start_combat", "params": {}},
    ).json()["ok"]

    import studio_plugin_combat.dice as combat_dice

    monkeypatch.setattr(combat_dice, "roll_d20", lambda rng=None: 1)

    miss = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Swing.",
                "action": "verb",
                "verb": "swing",
                "target": foe.id,
            },
        },
    )
    assert miss.json()["ok"] is True, miss.json()
    assert "miss" in miss.json()["message"].lower()
