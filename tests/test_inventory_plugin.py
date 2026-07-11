"""Inventory plugin integration tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.plugin_registry import clear_plugin_registry_for_tests
from backend.plugin_upload import load_all_plugins
from backend.session_store import reset_session_store
from campaign_rpg_engine import ObjectAction, clear_event_listeners_for_tests, clear_turn_verbs_for_tests
from campaign_rpg_engine.prompt_slots.registry import clear_prompt_slots_for_tests
from reference_handlers import register_reference_handlers
from tests.world_helpers import add_object_action, create_agent, create_object, get_session

_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


@pytest.fixture(autouse=True)
def _fresh_inventory_plugin_state():
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


def _enable_inventory(client):
    response = client.post("/api/plugins/inventory/enable")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def _setup_pickup_ball(*, with_drink: bool = False):
    agent = create_agent(
        name="Carrier",
        position=(0, 0),
        personality="Hauls things.",
        is_player=True,
    )
    ball = create_object(
        name="Travel Mug",
        position=(0, 1),
        passive_description="A dented mug.",
        blocks_movement=False,
    )
    add_object_action(
        ball.id,
        ObjectAction(
            name="pick_up",
            range=1,
            handler_id="inventory_pick_up",
            result="You pick up {object}.",
            passive_result="{actor} picks up {object}.",
        ),
    )
    if with_drink:
        add_object_action(
            ball.id,
            ObjectAction(
                name="drink",
                range=1,
                handler_id="inventory_consume",
                result="You drink the coffee. It's gone.",
                passive_result="{actor} drinks something.",
            ),
        )
    return agent, ball


def test_inventory_plugin_in_catalog(client):
    response = client.get("/api/plugins")
    assert response.status_code == 200
    ids = {p["id"] for p in response.json()["plugins"]}
    assert "inventory" in ids


def test_pick_up_and_drop_via_panel(client):
    _enable_inventory(client)
    agent, ball = _setup_pickup_ball()
    client.post("/api/active-agent", json={"name_or_id": agent.id})

    turn = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Grab the ball.",
                "action": "interact",
                "target": ball.id,
                "verb": "pick_up",
            },
        },
    )
    assert turn.status_code == 200
    assert turn.json()["ok"] is True

    session = get_session()
    assert session.area.get_object_by_id(ball.id) is None
    inv = session.get_extension("inventory")
    assert ball.id in {item["item_id"] for item in inv["by_agent"][agent.id]}

    panel = client.get("/api/plugins/inventory/panel").json()
    assert panel["ok"] is True
    assert "Travel Mug" in str(panel["panel"])

    drop = client.post(
        "/api/plugins/inventory/action",
        json={"action_id": "drop_item", "params": {"item_id": ball.id}},
    )
    assert drop.status_code == 200
    drop_body = drop.json()
    assert drop_body["ok"] is True
    assert drop_body["object_id"] == ball.id
    assert session.area.get_object_by_id(ball.id) is not None
    assert inv["by_agent"][agent.id] == []


def test_drop_via_turn_verb(client):
    _enable_inventory(client)
    agent, ball = _setup_pickup_ball()
    client.post("/api/active-agent", json={"name_or_id": agent.id})

    client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick up.",
                "action": "interact",
                "target": ball.id,
                "verb": "pick_up",
            },
        },
    )

    drop_turn = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Drop it.",
                "action": "verb",
                "verb": "drop",
                "target": ball.id,
            },
        },
    )
    assert drop_turn.status_code == 200
    assert drop_turn.json()["ok"] is True
    session = get_session()
    assert session.area.get_object_by_id(ball.id) is not None
    assert session.get_extension("inventory")["by_agent"][agent.id] == []


def test_inventory_prompt_slot_format(client):
    _enable_inventory(client)
    agent, ball = _setup_pickup_ball()
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick up.",
                "action": "interact",
                "target": ball.id,
                "verb": "pick_up",
            },
        },
    )

    slots = client.get("/api/prompt-slots").json()["slots"]
    inventory = next(item for item in slots if item["name"] == "inventory")
    preview = inventory["preview"]
    assert "Items in your Inventory:" in preview
    assert f"Travel Mug ({ball.id}) [drop]" in preview
    assert '"action": "verb"' in preview
    assert "verb = action name" in preview.lower() or "action name" in preview.lower()


def test_plugin_slot_block_preview_includes_inventory(client):
    _enable_inventory(client)
    agent, ball = _setup_pickup_ball()
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick up.",
                "action": "interact",
                "target": ball.id,
                "verb": "pick_up",
            },
        },
    )

    blocks = client.get("/api/prompt-blocks").json()["blocks"]
    blocks.append({"type": "plugin_slot", "name": "inventory"})
    preview = client.post("/api/prompt-blocks/preview", json={"blocks": blocks}).json()
    inv_block = next(b for b in preview["blocks"] if b.get("name") == "inventory")
    assert "Items in your Inventory:" in inv_block.get("preview", "")
    assert f"Travel Mug ({ball.id}) [drop]" in inv_block.get("preview", "")


def test_inventory_state_round_trips_in_export(client):
    _enable_inventory(client)
    agent, ball = _setup_pickup_ball()
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick up.",
                "action": "interact",
                "target": ball.id,
                "verb": "pick_up",
            },
        },
    )

    export = client.get("/api/session/export").json()
    assert export["extensions"]["inventory"]["by_agent"][agent.id]

    reset_session_store()
    client.post("/api/session/import", json=export)
    state = client.get("/api/state?include_private=1").json()
    carried = state["extensions"]["inventory"]["by_agent"][agent.id]
    assert carried[0]["item_id"] == ball.id
    assert get_session().area.get_object_by_id(ball.id) is None


def test_inventory_only_actions_hidden_from_passive_vision(client):
    _enable_inventory(client)
    agent, mug = _setup_pickup_ball(with_drink=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})

    blocks = client.get("/api/prompt-blocks").json()["blocks"]
    blocks.append({"type": "slot", "name": "passive_vision"})
    preview = client.post("/api/prompt-blocks/preview", json={"blocks": blocks}).json()
    passive = next(b for b in preview["blocks"] if b.get("name") == "passive_vision")
    text = passive.get("preview", "")
    assert "Travel Mug" in text
    assert "pick_up" in text
    assert "drink" not in text


def test_grid_actions_not_listed_as_inventory_verbs(client):
    _enable_inventory(client)
    agent, ball = _setup_pickup_ball(with_drink=False)
    add_object_action(
        ball.id,
        ObjectAction(
            name="kick",
            range=1,
            handler_id="random_move_self",
            result="You kick {object}.",
            passive_result="{actor} kicks {object}.",
        ),
    )
    add_object_action(
        ball.id,
        ObjectAction(
            name="eat",
            range=1,
            handler_id="inventory_consume",
            result="You eat {object}.",
            passive_result="{actor} eats something.",
        ),
    )
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick up.",
                "action": "interact",
                "target": ball.id,
                "verb": "pick_up",
            },
        },
    )

    slots = client.get("/api/prompt-slots").json()["slots"]
    inventory = next(item for item in slots if item["name"] == "inventory")
    preview = inventory["preview"]
    assert "[eat]" in preview
    assert "[kick]" not in preview

    verbs = {v["id"] for v in client.get("/api/turn-verbs").json()["verbs"]}
    assert "eat" in verbs
    assert "kick" not in verbs


def test_drink_via_turn_verb_after_pickup(client):
    _enable_inventory(client)
    agent, mug = _setup_pickup_ball(with_drink=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})

    pickup = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick up the mug.",
                "action": "interact",
                "target": mug.id,
                "verb": "pick_up",
            },
        },
    )
    assert pickup.status_code == 200
    assert pickup.json()["ok"] is True

    session = get_session()
    inv = session.get_extension("inventory")
    assert mug.id in {item["item_id"] for item in inv["by_agent"][agent.id]}

    slots = client.get("/api/prompt-slots").json()["slots"]
    inventory = next(item for item in slots if item["name"] == "inventory")
    assert f"[drop] [drink]" in inventory["preview"] or "[drink]" in inventory["preview"]

    drink = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Drink the coffee.",
                "action": "verb",
                "verb": "drink",
                "target": mug.id,
            },
        },
    )
    assert drink.status_code == 200
    assert drink.json()["ok"] is True
    assert "coffee" in drink.json()["message"].lower()
    assert inv["by_agent"][agent.id] == []


def test_drink_on_grid_is_blocked(client):
    _enable_inventory(client)
    agent, mug = _setup_pickup_ball(with_drink=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})

    drink = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Try to drink from the map.",
                "action": "interact",
                "target": mug.id,
                "verb": "drink",
            },
        },
    )
    assert drink.status_code == 200
    body = drink.json()
    assert body["ok"] is False or "pick up" in body.get("message", "").lower()
    assert get_session().area.get_object_by_id(mug.id) is not None


def test_drink_via_plugins_panel(client):
    _enable_inventory(client)
    agent, mug = _setup_pickup_ball(with_drink=True)
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Pick up.",
                "action": "interact",
                "target": mug.id,
                "verb": "pick_up",
            },
        },
    )

    use = client.post(
        "/api/plugins/inventory/action",
        json={
            "action_id": "use_item",
            "params": {"item_id": mug.id, "action": "drink"},
        },
    )
    assert use.status_code == 200
    assert use.json()["ok"] is True
    session = get_session()
    assert session.get_extension("inventory")["by_agent"][agent.id] == []
