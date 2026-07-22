"""GM setup UX: entity form sections, combat_attack templates, panel helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend.app import create_app
from backend.initiative import put_initiative
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
from tests.world_helpers import create_agent, create_object, get_session

_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


@pytest.fixture(autouse=True)
def _fresh_state():
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


def _enable_all(client):
    for pid in ("inventory", "skills", "combat"):
        assert client.post(f"/api/plugins/{pid}/enable").json()["ok"] is True


def test_entity_form_sections_and_merge(client):
    _enable_all(client)
    obj = create_object(name="Blade", position=(1, 1), passive_description="Sharp.")
    sections = client.get("/api/entity-form-sections", params={"kind": "object", "entity_id": obj.id})
    assert sections.status_code == 200
    body = sections.json()
    assert body["ok"] is True
    combat_sections = [s for s in body["sections"] if s["plugin_id"] == "combat"]
    assert combat_sections
    prefix = f"efs_combat_{combat_sections[0]['section_id']}_"
    merged = client.post(
        "/api/entity-form-sections/merge",
        json={
            "kind": "object",
            "private_data": "",
            "values": {
                f"{prefix}kind": "weapon",
                f"{prefix}range": "2",
                f"{prefix}attack_stat": "STR",
                f"{prefix}accuracy_bonus": "1",
                f"{prefix}damage": "1d8+1",
                f"{prefix}weapon_req": "STR:12",
            },
        },
    )
    assert merged.status_code == 200
    data = json.loads(merged.json()["private_data"])
    assert data["combat_plugin"]["slot"] == "weapon"
    assert "action" not in data["combat_plugin"]
    assert data["combat_plugin"]["range"] == 2
    assert data["combat_plugin"]["req"]["STR"] == 12


def test_set_max_hp_panel_action(client):
    _enable_all(client)
    agent = create_agent(name="Hero", position=(0, 0), personality="x", is_player=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    response = client.post(
        "/api/plugins/combat/action",
        json={"action_id": "set_max_hp", "params": {"max_hp": 18}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    private = json.loads(get_session().get_agent(agent.id).private_data)
    assert private["combat_plugin"]["hp"] == 18
    assert private["combat_plugin"]["max_hp"] == 18


def test_combat_attack_templates_on_hit(client, monkeypatch):
    _enable_all(client)
    fighter = create_agent(name="Fighter", position=(0, 0), personality="x", is_player=True)
    foe = create_agent(name="Foe", position=(1, 0), personality="x")
    session = get_session()
    put_initiative(session, enabled=True, order=[fighter.id, foe.id], index=0)
    client.post("/api/active-agent", json={"name_or_id": fighter.id})

    sword = {
        "item_id": "obj_sword_1",
        "name": "Longsword",
        "private_data": json.dumps(
            {
                "combat_plugin": {
                    "slot": "weapon",
                    "range": 1,
                    "attack_stat": "STR",
                    "accuracy_bonus": 20,
                    "damage": "1d4",
                    "req": {},
                }
            }
        ),
        "actions": {
            "swing": {
                "kind": "interact",
                "range": 1,
                "handler_id": "combat_attack",
                "handler_params": {
                    "miss_result": "MISS {target} roll={attack_roll}",
                    "miss_passive": "{actor} whiffs",
                },
                "result": "HIT {target} dmg={damage_total} hp={target_hp}",
                "passive_result": "{actor} smites {target}",
                "enabled": True,
            }
        },
    }
    inv = session.get_extension("inventory") or {"by_agent": {}}
    inv.setdefault("by_agent", {})[fighter.id] = [sword]
    session.set_extension("inventory", inv)

    assert (
        client.post(
            "/api/turn/manual",
            json={
                "compound_turn": {
                    "reasoning": "Equip.",
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

    monkeypatch.setattr(combat_dice, "roll_d20", lambda rng=None: 15)
    monkeypatch.setattr(
        combat_dice,
        "roll_damage",
        lambda expr, rng=None: {
            "expr": expr,
            "rolls": [3],
            "modifier": 0,
            "total": 3,
            "detail": "1d4=3",
        },
    )

    hit = client.post(
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
    assert hit.json()["ok"] is True, hit.json()
    msg = hit.json()["message"].lower()
    assert "hit" in msg
    assert "dmg=3" in msg or "3" in msg


def test_grant_from_template_panel(client, tmp_path, monkeypatch):
    _enable_all(client)
    agent = create_agent(name="Carrier", position=(0, 0), personality="x", is_player=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})

    # Write a minimal object template into the templates dir used by the API.
    from backend import entity_templates_api as eta

    monkeypatch.setattr(eta, "ENTITY_TEMPLATES_DIR", tmp_path)
    template = {
        "template_version": 1,
        "kind": "object",
        "name": "Potion",
        "passive_description": "A vial.",
        "description": "Red liquid.",
        "private_data": "",
        "actions": {},
        "width": 1,
        "height": 1,
        "blocks_movement": False,
        "appearance": "",
    }
    (tmp_path / "potion.json").write_text(json.dumps(template), encoding="utf-8")

    response = client.post(
        "/api/plugins/inventory/action",
        json={"action_id": "grant_from_template", "params": {"template_id": "potion"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    items = get_session().get_extension("inventory")["by_agent"][agent.id]
    assert any(i.get("name") == "Potion" for i in items)
