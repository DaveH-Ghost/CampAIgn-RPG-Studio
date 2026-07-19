"""Skills plugin integration tests."""

from pathlib import Path

import pytest
from backend.app import create_app
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
from tests.world_helpers import add_object_action, create_agent, create_object, get_session

_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


@pytest.fixture(autouse=True)
def _fresh_skills_plugin_state():
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


def _enable_skills(client):
    response = client.post("/api/plugins/skills/enable")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def _setup_lock(*, dc: str = "15", skill: str | None = "lockpicking"):
    agent = create_agent(
        name="Thief",
        position=(0, 0),
        personality="Sneaky.",
        is_player=True,
    )
    lock = create_object(
        name="Chest Lock",
        position=(0, 1),
        passive_description="A sturdy lock.",
        blocks_movement=False,
    )
    params = {"stat": "DEX", "dc": dc}
    if skill:
        params["skill"] = skill
    params["fail_result"] = "The lock holds firm."
    params["fail_passive"] = "{actor} fails to pick the lock."
    add_object_action(
        lock.id,
        ObjectAction(
            name="pick_lock",
            range=1,
            handler_id="skill_check",
            handler_params=params,
            result="You pick the lock open.",
            passive_result="{actor} picks the lock.",
        ),
    )
    return agent, lock


def test_skills_plugin_in_catalog(client):
    response = client.get("/api/plugins")
    assert response.status_code == 200
    ids = {p["id"] for p in response.json()["plugins"]}
    assert "skills" in ids


def test_defaults_all_tens_in_prompt(client):
    _enable_skills(client)
    agent = create_agent(name="Hero", position=(1, 1), personality=".", is_player=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    slots = client.get("/api/prompt-slots").json()["slots"]
    skills = next(item for item in slots if item["name"] == "skills")
    preview = skills["preview"]
    assert "Your abilities:" in preview
    for name in ("CON", "STR", "DEX", "WIS", "INT", "CHM"):
        assert f"{name} 10 (+0)" in preview
    assert "Skills: (none)" in preview


def test_skills_template_vars_merge_when_enabled(client):
    assert "raw_roll" not in {
        item["name"] for item in client.get("/api/interact-template-vars").json()["vars"]
    }
    _enable_skills(client)
    vars_list = client.get("/api/interact-template-vars").json()["vars"]
    by_name = {item["name"]: item for item in vars_list}
    assert by_name["actor"]["source"] == "core"
    for name in ("raw_roll", "roll_bonus", "modified_roll", "dc_target"):
        assert by_name[name]["source"] == "plugin"
        assert by_name[name]["plugin_id"] == "skills"
        assert by_name[name]["placeholder"] == "{" + name + "}"


def test_skill_check_pass_substitutes_roll_vars(client, monkeypatch):
    _enable_skills(client)
    agent, lock = _setup_lock(dc="10")
    located = get_session().find_object(lock.id)
    assert located is not None
    _area_id, obj = located
    action = obj.actions["pick_lock"]
    action.result = "Rolled {raw_roll}{roll_bonus}={modified_roll} vs {dc_target}."
    action.passive_result = "{actor} totals {modified_roll}."
    import studio_plugin_skills.dice as skills_dice

    monkeypatch.setattr(skills_dice, "roll_d20", lambda rng=None: 15)

    client.post("/api/active-agent", json={"name_or_id": agent.id})
    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick it.",
                "action": "interact",
                "target": lock.id,
                "verb": "pick_lock",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "Rolled 15+0=15 vs 10." in body["message"]
    live = get_session().get_agent(agent.id)
    assert live is not None
    assert "totals 15" in live.passive_result


def test_skill_check_pass_uses_success_templates(client, monkeypatch):
    _enable_skills(client)
    agent, lock = _setup_lock(dc="10")
    import studio_plugin_skills.dice as skills_dice

    monkeypatch.setattr(skills_dice, "roll_d20", lambda rng=None: 15)

    client.post("/api/active-agent", json={"name_or_id": agent.id})
    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick it.",
                "action": "interact",
                "target": lock.id,
                "verb": "pick_lock",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "pick the lock open" in body["message"].lower()
    assert "lock holds" not in body["message"].lower()


def test_skill_check_fail_uses_fail_templates(client, monkeypatch):
    _enable_skills(client)
    agent, lock = _setup_lock(dc="20")
    import studio_plugin_skills.dice as skills_dice

    monkeypatch.setattr(skills_dice, "roll_d20", lambda rng=None: 2)

    client.post("/api/active-agent", json={"name_or_id": agent.id})
    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Try.",
                "action": "interact",
                "target": lock.id,
                "verb": "pick_lock",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "lock holds firm" in body["message"].lower()
    session = get_session()
    live = session.get_agent(agent.id)
    assert live is not None
    assert "fails to pick the lock" in live.passive_result


def test_skill_bonus_applies(client, monkeypatch):
    _enable_skills(client)
    agent, lock = _setup_lock(dc="15", skill="lockpicking")
    import json

    import studio_plugin_skills.dice as skills_dice

    monkeypatch.setattr(skills_dice, "roll_d20", lambda rng=None: 10)
    payload = {
        "skills_plugin": {
            "stats": {"DEX": 10},
            "skills": {"lockpicking": 5},
        }
    }
    get_session().set_entity_private_data(agent.id, json.dumps(payload))

    client.post("/api/active-agent", json={"name_or_id": agent.id})
    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Boosted.",
                "action": "interact",
                "target": lock.id,
                "verb": "pick_lock",
            },
        },
    )
    assert response.status_code == 200
    # 10 + 0 + 5 = 15 vs DC 15
    assert "pick the lock open" in response.json()["message"].lower()


def test_panel_shows_active_agent_sheet(client):
    _enable_skills(client)
    agent = create_agent(name="Hero", position=(1, 1), personality=".", is_player=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    panel = client.get("/api/plugins/skills/panel").json()
    assert panel["ok"] is True
    text = str(panel["panel"])
    assert "Hero" in text
    assert "STR" in text
    assert "skills_plugin" in text
    assert "init_stats" in text


def test_init_stats_writes_private_data(client):
    _enable_skills(client)
    agent = create_agent(name="Hero", position=(1, 1), personality=".", is_player=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    assert not (get_session().get_agent(agent.id).private_data or "").strip()

    init = client.post(
        "/api/plugins/skills/action",
        json={"action_id": "init_stats", "params": {}},
    )
    assert init.status_code == 200
    body = init.json()
    assert body["ok"] is True

    live = get_session().get_agent(agent.id)
    assert live is not None
    assert "skills_plugin" in live.private_data
    assert '"STR": 10' in live.private_data
    assert '"CON": 10' in live.private_data

    again = client.post(
        "/api/plugins/skills/action",
        json={"action_id": "init_stats", "params": {}},
    )
    assert again.status_code == 400
    assert "already" in str(again.json().get("detail", "")).lower()

    panel = client.get("/api/plugins/skills/panel").json()
    assert "init_stats" not in str(panel["panel"])


def test_pass_handler_inventory_pick_up(client, monkeypatch):
    _enable_skills(client)
    assert client.post("/api/plugins/inventory/enable").json()["ok"] is True

    agent = create_agent(
        name="Scout",
        position=(0, 0),
        personality=".",
        is_player=True,
    )
    relic = create_object(
        name="Relic",
        position=(0, 1),
        passive_description="A glowing relic.",
        blocks_movement=False,
    )
    add_object_action(
        relic.id,
        ObjectAction(
            name="snatch",
            range=1,
            handler_id="skill_check",
            handler_params={
                "stat": "DEX",
                "dc": "10",
                "pass_handler": "inventory_pick_up",
                "fail_handler": "delete_self",
                "fail_result": "The plate snaps shut.",
                "fail_passive": "{actor} triggers the plate.",
            },
            result="You snatch the relic.",
            passive_result="{actor} snatches the relic.",
        ),
    )
    import studio_plugin_skills.dice as skills_dice

    monkeypatch.setattr(skills_dice, "roll_d20", lambda rng=None: 15)
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Grab it.",
                "action": "interact",
                "target": relic.id,
                "verb": "snatch",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "snatch the relic" in response.json()["message"].lower()

    session = get_session()
    assert session.find_object(relic.id) is None
    inv = session.get_extension("inventory")
    assert relic.id in {item["item_id"] for item in inv["by_agent"][agent.id]}


def test_fail_handler_delete_self(client, monkeypatch):
    _enable_skills(client)
    agent = create_agent(
        name="Scout",
        position=(0, 0),
        personality=".",
        is_player=True,
    )
    bait = create_object(
        name="Bait",
        position=(0, 1),
        passive_description="Suspicious bait.",
        blocks_movement=False,
    )
    add_object_action(
        bait.id,
        ObjectAction(
            name="grab",
            range=1,
            handler_id="skill_check",
            handler_params={
                "stat": "DEX",
                "dc": "20",
                "fail_handler": "delete_self",
                "fail_result": "The bait vanishes.",
                "fail_passive": "{actor} loses the bait.",
            },
            result="You grab it.",
            passive_result="{actor} grabs it.",
        ),
    )
    import studio_plugin_skills.dice as skills_dice

    monkeypatch.setattr(skills_dice, "roll_d20", lambda rng=None: 2)
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Try.",
                "action": "interact",
                "target": bait.id,
                "verb": "grab",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "bait vanishes" in response.json()["message"].lower()
    assert get_session().find_object(bait.id) is None


def test_reject_skill_check_as_followup():
    from studio_plugin_skills.handlers import validate_skill_check_params

    err = validate_skill_check_params({"stat": "STR", "dc": "10", "pass_handler": "skill_check"})
    assert err is not None
    assert "cannot be skill_check" in err
