"""campaign-rpg-studio API tests (V0.3.1–0.4.0c2)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.session_store import get_session_store, reset_session_store
from backend.version import studio_version
from campaign_rpg_engine import AgentCompoundTurn, LLMResponse, ObjectAction, SessionResult
from tests.world_helpers import add_object_action, create_agent, create_object, edit_agent, edit_object

ROOM = "room"
HALL = "hall"


@pytest.fixture(autouse=True)
def _fresh_session_store():
    reset_session_store()
    yield
    reset_session_store()


@pytest.fixture
def client():
    return TestClient(create_app())


def _room(state: dict) -> dict:
    return state["areas"][ROOM]


def _active_block(state: dict) -> dict:
    return state["areas"][state["active_area_id"]]


def test_get_interaction_handlers_lists_reference_set(client):
    response = client.get("/api/interaction-handlers")
    assert response.status_code == 200
    data = response.json()
    ids = {item["id"] for item in data["handlers"]}
    assert {"delete_self", "random_move_self", "move_area", "sequence", "set_object_text", "set_action_enabled", "spawn_from_template"} <= ids
    assert "inventory_pick_up" not in ids
    move = next(h for h in data["handlers"] if h["id"] == "move_area")
    assert move.get("summary_template")
    field_names = {f["name"] for f in move.get("param_fields") or []}
    assert {"dest-area", "dest-at"} <= field_names


def test_get_interaction_handlers_includes_enabled_plugin_handlers(client):
    client.post("/api/plugins/inventory/enable")
    response = client.get("/api/interaction-handlers")
    ids = {item["id"] for item in response.json()["handlers"]}
    assert "inventory_pick_up" in ids
    assert "inventory_add_from_template" in ids
    add_handler = next(
        h for h in response.json()["handlers"] if h["id"] == "inventory_add_from_template"
    )
    fields = {f["name"]: f for f in add_handler.get("param_fields") or []}
    assert fields["template_id"]["type"] == "template_id"


def test_spawn_from_template_catalog_has_template_id(client):
    response = client.get("/api/interaction-handlers")
    spawn = next(h for h in response.json()["handlers"] if h["id"] == "spawn_from_template")
    fields = {f["name"]: f for f in spawn.get("param_fields") or []}
    assert fields["template_id"]["type"] == "template_id"
    assert fields["template_id"].get("kind") == "object"


def test_skill_check_catalog_includes_param_fields(client):
    client.post("/api/plugins/skills/enable")
    response = client.get("/api/interaction-handlers")
    skill = next(h for h in response.json()["handlers"] if h["id"] == "skill_check")
    assert "skill_check" in (skill.get("summary_template") or "")
    names = {f["name"] for f in skill.get("param_fields") or []}
    assert {"stat", "dc", "pass_handler", "fail_handler"} <= names
    pass_ref = next(f for f in skill["param_fields"] if f["name"] == "pass_handler")
    assert pass_ref["type"] == "handler_ref"
    assert pass_ref.get("param_prefix") == "pass_"


def test_player_turn_assist_empty_without_inventory(client):
    response = client.get("/api/player-turn-assist")
    assert response.status_code == 200
    assert response.json()["targets"] == []


def test_player_turn_assist_lists_carried_item_verbs(client):
    from campaign_rpg_engine import ObjectAction

    assert client.post("/api/plugins/inventory/enable").json()["ok"] is True
    agent = create_agent(
        name="Hero",
        position=(0, 0),
        personality="Hauls things.",
        is_player=True,
    )
    ball = create_object(
        name="Ball",
        position=(0, 1),
        passive_description="A ball.",
        blocks_movement=False,
    )
    add_object_action(
        ball.id,
        ObjectAction(
            name="pick_up",
            range=1,
            handler_id="inventory_pick_up",
            result="You pick it up.",
            passive_result="picks up the ball.",
        ),
    )
    add_object_action(
        ball.id,
        ObjectAction(
            name="drink",
            range=0,
            handler_id="inventory_consume",
            result="You drink.",
            passive_result="drinks.",
        ),
    )
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    pick = client.post(
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
    assert pick.status_code == 200
    assert pick.json()["ok"] is True
    assist = client.get("/api/player-turn-assist").json()
    assert len(assist["targets"]) == 1
    row = assist["targets"][0]
    assert row["id"] == ball.id
    assert "drop" in row["verbs"]
    assert "drink" in row["verbs"]
    assert row.get("plugin_id") == "inventory"

def test_get_state_includes_vision_units(client):
    response = client.get("/api/state")
    data = response.json()
    assert data.get("vision_units") == ""
    assert data.get("vision_units_per_tile") is None


def test_put_vision_units(client):
    response = client.put(
        "/api/vision-units",
        json={"units": "ft", "units_per_tile": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["vision_units"] == "ft"
    assert data["vision_units_per_tile"] == 5
    assert data["snapshot"]["vision_units"] == "ft"


def test_put_vision_units_rejects_invalid_units(client):
    response = client.put(
        "/api/vision-units",
        json={"units": "ft5", "units_per_tile": 5},
    )
    assert response.json()["ok"] is False


def test_get_state_includes_coordinate_mode(client):
    response = client.get("/api/state")
    data = response.json()
    assert data.get("coordinate_mode") == "full"


def test_put_coordinate_mode_relative_sets_dnd_defaults(client):
    response = client.put("/api/coordinate-mode", json={"mode": "relative"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["coordinate_mode"] == "relative"
    assert data["vision_units"] == "ft"
    assert data["vision_units_per_tile"] == 5
    assert data["snapshot"]["coordinate_mode"] == "relative"


def test_relative_coordinate_mode_prompt_preview(client):
    client.put("/api/coordinate-mode", json={"mode": "relative"})
    response = client.get("/api/prompt-blocks")
    assert response.status_code == 200
    blocks = response.json()["blocks"]
    grid = next(b for b in blocks if b.get("name") == "grid_description")
    assert "grid-based world" in grid["preview"]
    assert "northwest" not in grid["preview"]
    rules = next(b for b in blocks if b.get("name") == "compound_rules")
    assert "x,y" not in rules["preview"]
    output = next(b for b in blocks if b.get("name") == "output_format")
    assert '"2,3"' not in output["preview"]


def test_create_agent_blocks_movement(client):
    agent = create_agent(
        name="Guard",
        position=(1, 1),
        personality="Stoic.",
        blocks_movement=True,
        movement_exceptions=["agent_01"],
    )
    state = client.get("/api/state").json()
    saved = next(a for a in state["agents"] if a["id"] == agent.id)
    assert saved["blocks_movement"] is True
    assert saved["movement_exceptions"] == ["agent_01"]


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["version"] == studio_version()
    from campaign_rpg_engine import __version__ as engine_version

    assert data["campaign_rpg_engine_version"] == engine_version


def test_interact_template_vars(client):
    response = client.get("/api/interact-template-vars")
    assert response.status_code == 200
    data = response.json()
    names = {item["name"] for item in data["vars"]}
    assert "actor" in names
    assert "object_start" in names
    assert "actor_end_area" in names
    assert "{actor}" in data["vars"][0]["placeholder"]
    assert all(item.get("source") == "core" for item in data["vars"])


def test_state_returns_multi_area_snapshot(client):
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()

    assert data["active_area_id"] == ROOM
    assert ROOM in data["areas"]
    assert HALL in data["areas"]
    assert _room(data)["grid"] == {"min_x": 0, "max_x": 4, "min_y": 0, "max_y": 4}
    assert data["active_agent_id"] == "agent_01"
    assert data["session_turn"] == 0
    assert "passive_vision" in data
    assert "You are at (1, 1)" in data["passive_vision"]

    assert len(data["agents"]) == 1
    assert data["agents"][0]["name"] == "Explorer"
    assert data["agents"][0]["area_id"] == ROOM
    assert data["agents"][0]["appearance"] == "tokens/explorer.svg"
    assert "personality" in data["agents"][0]
    assert data["agents"][0]["move_speed"] is None

    room_objects = _room(data)["objects"]
    object_ids = {o["id"] for o in room_objects}
    assert "obj_ball_01" in object_ids
    assert "obj_sign_01" in object_ids
    ball = next(o for o in room_objects if o["id"] == "obj_ball_01")
    assert "kick" in ball["actions"]
    assert ball["actions_detail"]["kick"]["range"] == 1
    assert ball["actions_detail"]["kick"]["handler_id"] == "random_move_self"
    assert isinstance(_room(data)["objects"], list)
    assert isinstance(_room(data)["recent_events"], list)
    assert isinstance(_active_block(data)["objects"], list)


def test_hall_area_has_objects_array(client):
    data = client.get("/api/state").json()
    assert isinstance(data["areas"][HALL]["objects"], list)
    assert data["areas"][HALL]["objects"] == []


def test_post_event_success(client):
    response = client.post(
        "/api/event",
        json={"text": "Thunder rumbles overhead."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "Thunder" in data["message"]
    events = data["snapshot"]["areas"][ROOM]["recent_events"]
    assert events == [{"session_turn": 0, "text": "Thunder rumbles overhead."}]
    assert data["snapshot"]["session_turn"] == 0
    assert "Thunder rumbles overhead." not in data["snapshot"]["passive_vision"]


def test_post_event_empty_rejected(client):
    response = client.post("/api/event", json={"text": ""})
    assert response.status_code == 422


def test_post_event_whitespace_fails(client):
    response = client.post("/api/event", json={"text": "   "})
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_post_event_via_state(client):
    client.post("/api/event", json={"text": "A door slams."})
    state = client.get("/api/state").json()
    assert _room(state)["recent_events"][-1]["text"] == "A door slams."


def test_post_event_targeted_agents(client):
    goblin = create_agent(
        name="Goblin",
        position=(0, 0),
        personality="Grumpy.",
    )

    response = client.post(
        "/api/event",
        json={"text": "A whisper only Goblin hears.", "agent_ids": [goblin.id]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "Goblin" in data["message"]
    assert _room(data["snapshot"])["recent_events"] == []


def test_post_event_empty_agent_ids_broadcasts(client):
    create_agent(name="Goblin", position=(0, 0), personality="Grumpy.")
    response = client.post(
        "/api/event",
        json={"text": "Everyone hears.", "agent_ids": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert _room(data["snapshot"])["recent_events"] == [
        {"session_turn": 0, "text": "Everyone hears."}
    ]
def test_post_active_area_switch(client):
    response = client.post("/api/active-area", json={"area_id": HALL})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["snapshot"]["active_area_id"] == HALL
    assert isinstance(data["snapshot"]["areas"][HALL]["objects"], list)

    state = client.get("/api/state").json()
    assert state["active_area_id"] == HALL


def test_post_active_area_unknown(client):
    response = client.post("/api/active-area", json={"area_id": "attic"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False


def test_create_object_scoped_to_active_area(client):
    client.post("/api/active-area", json={"area_id": HALL})
    create_object(name="Bench", position=(2, 2), passive_description="A bench.")

    state = client.get("/api/state").json()
    hall_names = {o["name"] for o in state["areas"][HALL]["objects"]}
    room_names = {o["name"] for o in state["areas"][ROOM]["objects"]}
    assert "Bench" in hall_names
    assert "Bench" not in room_names


def test_static_token_assets(client):
    for path in (
        "/static/tokens/explorer.svg",
        "/static/tokens/ball.svg",
        "/static/tokens/sign.svg",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert "svg" in response.headers.get("content-type", "").lower()


def test_create_object_appearance(client):
    create_object(
        name="Token Crate",
        position=(3, 3),
        appearance="tokens/ball.svg",
    )

    state = client.get("/api/state").json()
    crate = next(o for o in _room(state)["objects"] if o["name"] == "Token Crate")
    assert crate["appearance"] == "tokens/ball.svg"


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "CampAIgn RPG Studio" in response.text
    assert 'id="app-subtitle"' in response.text
    assert f"V{studio_version()}" in response.text
    assert 'id="grid"' in response.text
    assert 'id="active-area-select"' in response.text
    assert 'id="create-area"' in response.text
    assert 'id="edit-area"' in response.text
    assert 'id="delete-area"' in response.text
    assert 'id="last-prompt"' in response.text
    assert 'id="last-response"' in response.text
    assert 'id="player-turn-panel"' in response.text


def _fake_compound_response(_prompt):
    return LLMResponse(
        parsed=AgentCompoundTurn(
            reasoning="stay and speak",
            action="none",
            say="Hello from the test.",
        ),
        raw_response="{}",
        prompt_tokens=512,
        completion_tokens=42,
        total_tokens=554,
    )


def test_post_turn_success(client, monkeypatch):
    monkeypatch.setattr(
        "backend.turn_runner.get_compound_turn",
        _fake_compound_response,
    )

    response = client.post("/api/turn", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["snapshot"]["session_turn"] == 1
    assert "areas" in data["snapshot"]
    assert "prompt" in data
    assert data["llm_response"] == "{}"
    assert data["prompt_tokens"] == 512
    assert data["completion_tokens"] == 42
    assert data["total_tokens"] == 554
    assert isinstance(data["prompt_tokens_estimate"], int)
    assert data["prompt_tokens_estimate"] > 0


def test_get_prompt(client):
    response = client.get("/api/prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["prompt"]) > 100
    assert isinstance(data["prompt_tokens"], int)
    assert data["prompt_tokens"] > 0


def test_get_prompt_unknown_agent(client):
    response = client.get("/api/prompt", params={"agent_id": "nobody"})
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_get_prompt_blocks_default(client):
    response = client.get("/api/prompt-blocks")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["uses_default"] is True
    assert len(data["blocks"]) > 5
    assert data["blocks"][0]["type"] == "slot"


def test_put_prompt_blocks_reorder(client):
    base = client.get("/api/prompt-blocks").json()
    blocks = list(base["blocks"])
    blocks.insert(0, {"type": "text", "content": "API START\n"})
    put = client.put("/api/prompt-blocks", json={"blocks": blocks})
    assert put.status_code == 200
    assert put.json()["ok"] is True
    assert put.json()["uses_default"] is False

    prompt = client.get("/api/prompt").json()["prompt"]
    assert prompt.startswith("API START")


def test_put_prompt_blocks_invalid(client):
    response = client.put(
        "/api/prompt-blocks",
        json={"blocks": [{"type": "slot", "name": "bad_slot"}]},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_reset_prompt_blocks(client):
    blocks = client.get("/api/prompt-blocks").json()["blocks"]
    blocks[0] = {"type": "text", "content": "TEMP\n"}
    client.put("/api/prompt-blocks", json={"blocks": blocks})
    reset = client.post("/api/prompt-blocks/reset")
    assert reset.status_code == 200
    assert reset.json()["uses_default"] is True


def test_get_prompt_slots(client):
    response = client.get("/api/prompt-slots")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    names = {item["name"] for item in data["slots"]}
    assert "passive_vision" in names
    assert "memory" in names
    assert "inventory" not in names
    assert "compound_rules" in data["editable_sections"]


def test_get_prompt_block_catalog(client):
    response = client.get("/api/prompt-block-catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    types = {entry["type"] for entry in data["block_types"]}
    assert types == {"slot", "plugin_slot", "text", "section"}
    assert "character" in data["slot_settings"]
    plugin_entry = next(item for item in data["block_types"] if item["type"] == "plugin_slot")
    plugin_names = {opt["name"] for opt in plugin_entry["options"]}
    assert "inventory" not in plugin_names

    client.post("/api/plugins/inventory/enable")
    enabled = client.get("/api/prompt-block-catalog").json()
    plugin_entry = next(
        item for item in enabled["block_types"] if item["type"] == "plugin_slot"
    )
    assert "inventory" in {opt["name"] for opt in plugin_entry["options"]}


def test_get_turn_verbs(client):
    response = client.get("/api/turn-verbs")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    ids = {verb["id"] for verb in data["verbs"]}
    assert "drop" not in ids

    client.post("/api/plugins/inventory/enable")
    enabled = client.get("/api/turn-verbs").json()
    ids = {verb["id"] for verb in enabled["verbs"]}
    assert "drop" in ids


def test_put_prompt_blocks_plugin_slot(client):
    client.post("/api/plugins/inventory/enable")
    blocks = client.get("/api/prompt-blocks").json()["blocks"]
    blocks.append({"type": "plugin_slot", "name": "inventory"})
    response = client.put("/api/prompt-blocks", json={"blocks": blocks})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    saved = client.get("/api/prompt-blocks").json()["blocks"]
    assert any(b.get("type") == "plugin_slot" and b.get("name") == "inventory" for b in saved)


def test_get_memory_modules(client):
    response = client.get("/api/memory-modules")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["default_id"] == "recent_turns"
    ids = {mod["id"] for mod in data["modules"]}
    assert ids == {"recent_turns", "salient_turns", "rolling_summary", "affinity"}
    salient = next(m for m in data["modules"] if m["id"] == "salient_turns")
    assert salient["options"][0]["flag"] == "memory-budget"
    recent = next(m for m in data["modules"] if m["id"] == "recent_turns")
    assert recent["options"][0]["flag"] == "memory-window"
    rolling = next(m for m in data["modules"] if m["id"] == "rolling_summary")
    assert len(rolling["options"]) == 3
    affinity = next(m for m in data["modules"] if m["id"] == "affinity")
    assert len(affinity["options"]) == 3
    assert {opt["flag"] for opt in affinity["options"]} == {
        "memory-summary-interval",
        "memory-summary-max",
        "memory-summary-tail",
    }


def test_create_agent_with_recent_turns_memory_window(client):
    agent = create_agent(
        name="Watcher",
        position=(2, 2),
        passive_description="A watcher.",
        description="Alert watcher.",
        personality="You watch.",
        memory_module="recent_turns",
        memory_window=5,
    )
    assert agent.memory.module_id == "recent_turns"
    state_agent = next(
        a for a in client.get("/api/state").json()["agents"] if a["name"] == "Watcher"
    )
    assert state_agent["memory_module"] == "recent_turns"


def test_create_agent_with_salient_memory(client):
    create_agent(
        name="Scribe",
        position=(1, 1),
        passive_description="A scribe.",
        description="Quiet scribe.",
        personality="You are a scribe.",
        memory_module="salient_turns",
        memory_budget=1200,
    )
    agent = next(
        a for a in client.get("/api/state").json()["agents"] if a["name"] == "Scribe"
    )
    assert agent["memory_module"] == "salient_turns"


def test_preview_prompt_blocks_character_options(client):
    base = client.get("/api/prompt-blocks").json()["blocks"]
    blocks = list(base)
    blocks[0] = {
        "type": "slot",
        "name": "character",
        "options": {
            "include_name": True,
            "include_personality": False,
            "include_description": False,
        },
    }
    response = client.post("/api/prompt-blocks/preview", json={"blocks": blocks})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    preview = data["blocks"][0]["preview"]
    assert preview.startswith("You are ")
    assert "Your personality:" not in preview


def test_preview_prompt_blocks_passive_vision_relative_bearing(client):
    client.put("/api/vision-units", json={"units": "ft", "units_per_tile": 5})
    base = client.get("/api/prompt-blocks").json()["blocks"]
    blocks = list(base)
    passive_index = next(
        i for i, block in enumerate(blocks) if block.get("name") == "passive_vision"
    )
    blocks[passive_index] = {
        "type": "slot",
        "name": "passive_vision",
        "options": {"include_relative_bearing": True},
    }
    response = client.post("/api/prompt-blocks/preview", json={"blocks": blocks})
    preview = response.json()["blocks"][passive_index]["preview"]
    assert "South of you, 15 ft away" in preview


def test_preview_prompt_blocks_passive_vision_options(client):
    base = client.get("/api/prompt-blocks").json()["blocks"]
    blocks = list(base)
    passive_index = next(
        i for i, block in enumerate(blocks) if block.get("name") == "passive_vision"
    )
    blocks[passive_index] = {
        "type": "slot",
        "name": "passive_vision",
        "options": {
            "include_you_are_at": False,
            "include_entity_coordinates": False,
        },
    }
    response = client.post("/api/prompt-blocks/preview", json={"blocks": blocks})
    assert response.status_code == 200
    preview = response.json()["blocks"][passive_index]["preview"]
    assert "You are at" not in preview
    assert "Ceramic Ball (obj_ball_01), (2, 2)" not in preview
    assert "Ceramic Ball (obj_ball_01)" in preview


def test_get_prompt_blocks_includes_slot_preview(client):
    response = client.get("/api/prompt-blocks")
    data = response.json()
    character = next(block for block in data["blocks"] if block.get("name") == "character")
    assert "preview" in character
    assert character["preview"]


def test_post_turn_gate_blocked(client, monkeypatch):
    def blocked(_agent_id=None):
        return SessionResult(ok=False, message="Cannot run turn: consolidation pending.")

    session = get_session_store().session
    monkeypatch.setattr(session, "gate_agent_turn", blocked)

    response = client.post("/api/turn", json={})
    assert response.json()["ok"] is False


def test_post_turn_missing_api_key(client, monkeypatch):
    def fail_llm(_prompt):
        raise RuntimeError("OPENROUTER_API_KEY not found.")

    monkeypatch.setattr("backend.turn_runner.get_compound_turn", fail_llm)
    response = client.post("/api/turn", json={})
    assert response.json()["ok"] is False


def test_e2e_edit_then_turn(client, monkeypatch):
    monkeypatch.setattr(
        "backend.turn_runner.get_compound_turn",
        _fake_compound_response,
    )

    create_object(
        name="E2E Crate",
        position=(2, 2),
        passive_description="A crate.",
        description="Test crate.",
    )

    mid = client.get("/api/state").json()
    assert any(o["name"] == "E2E Crate" for o in _room(mid)["objects"])

    turn = client.post("/api/turn", json={})
    data = turn.json()
    assert data["ok"] is True
    assert data["snapshot"]["session_turn"] == 1


def test_create_object(client):
    create_object(
        name="Test Crate",
        position=(2, 2),
        passive_description="A crate.",
        description="Wooden crate.",
    )

    state = client.get("/api/state").json()
    names = {o["name"] for o in _room(state)["objects"]}
    assert "Test Crate" in names


def test_create_object_blocks_movement(client):
    create_object(
        name="Passable",
        position=(1, 3),
        passive_description="Open.",
        blocks_movement=False,
    )

    state = client.get("/api/state").json()
    obj = next(o for o in _room(state)["objects"] if o["name"] == "Passable")
    assert obj["blocks_movement"] is False


def test_create_object_with_footprint(client):
    create_object(
        name="Table",
        position=(1, 1),
        passive_description="A table.",
        width=2,
        height=2,
    )

    state = client.get("/api/state").json()
    obj = next(o for o in _room(state)["objects"] if o["name"] == "Table")
    assert obj["width"] == 2
    assert obj["height"] == 2


def test_edit_object_footprint(client):
    shelf = create_object(name="Shelf", position=(0, 2), passive_description="A shelf.")
    edit_object(shelf.id, width=3, height=1)

    state = client.get("/api/state").json()
    obj = next(o for o in _room(state)["objects"] if o["id"] == shelf.id)
    assert obj["width"] == 3
    assert obj["height"] == 1


def test_create_hidden_object(client):
    create_object(
        name="Trap",
        position=(2, 2),
        passive_description="Hidden.",
        hidden=True,
        blocks_movement=False,
    )

    state = client.get("/api/state").json()
    obj = next(o for o in _room(state)["objects"] if o["name"] == "Trap")
    assert obj["hidden"] is True
    assert obj["blocks_movement"] is False


def test_add_trigger_action(client):
    plate = create_object(
        name="Plate",
        position=(1, 1),
        passive_description="A plate.",
        hidden=True,
        blocks_movement=False,
    )
    add_object_action(
        plate.id,
        ObjectAction(
            name="trip",
            range=0,
            result="(trigger)",
            passive_result="{actor} steps on the plate.",
            kind="trigger",
            halt_movement=True,
            delete_after_trigger=True,
        ),
    )

    state = client.get("/api/state").json()
    obj = next(o for o in _room(state)["objects"] if o["id"] == plate.id)
    detail = obj["actions_detail"]["trip"]
    assert detail["kind"] == "trigger"
    assert detail["halt_movement"] is True
    assert detail["delete_after_trigger"] is True


def test_put_entity_private_data(client):
    statue = create_object(name="Statue", position=(2, 2), passive_description="A statue.")

    response = client.put(
        "/api/entity-private-data",
        json={"entity_id": statue.id, "private_data": '{"hp": 25}'},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True

    state = client.get("/api/state").json()
    obj = next(o for o in _room(state)["objects"] if o["id"] == statue.id)
    assert obj["private_data"] == '{"hp": 25}'


def test_edit_object_movement_exceptions(client):
    gate = create_object(name="Gate", position=(0, 4), passive_description="A gate.")
    edit_object(gate.id, movement_exceptions=["agent_01"])

    state = client.get("/api/state").json()
    obj = next(o for o in _room(state)["objects"] if o["id"] == gate.id)
    assert obj["blocks_movement"] is True
    assert obj["movement_exceptions"] == ["agent_01"]


def test_command_dispatch_create_object(client):
    """Frontend still posts CLI lines; keep one compatibility smoke test."""
    response = client.post(
        "/api/command",
        json={
            "line": 'create-object name "CLI Crate" pdesc "From command." at 2,2',
        },
    )
    data = response.json()
    assert data["ok"] is True
    assert "snapshot" in data
    assert any(
        o["name"] == "CLI Crate"
        for o in data["snapshot"]["areas"]["room"]["objects"]
    )


def test_post_command_invalid(client):
    response = client.post(
        "/api/command",
        json={"line": "not-a-real-command"},
    )
    assert response.json()["ok"] is False


def test_post_active_agent(client):
    create_agent(
        name="Goblin",
        position=(0, 0),
        passive_description="A goblin.",
        description="Small goblin.",
        personality="You are a goblin.",
    )

    response = client.post(
        "/api/active-agent",
        json={"name_or_id": "Goblin"},
    )
    assert response.json()["ok"] is True

    state = client.get("/api/state").json()
    active = next(a for a in state["agents"] if a["name"] == "Goblin")
    assert state["active_agent_id"] == active["id"]


def test_post_active_agent_unknown(client):
    response = client.post(
        "/api/active-agent",
        json={"name_or_id": "Nobody"},
    )
    assert response.json()["ok"] is False


def test_create_agent_with_move_speed(client):
    create_agent(
        name="Scout",
        position=(0, 0),
        passive_description="A scout.",
        description="Fast scout.",
        personality="You are a scout.",
        move_speed=3,
    )

    scout = next(a for a in client.get("/api/state").json()["agents"] if a["name"] == "Scout")
    assert scout["move_speed"] == 3


def test_edit_agent_move_speed(client):
    walker = create_agent(
        name="Walker",
        position=(0, 0),
        passive_description="A walker.",
        description="Slow walker.",
        personality="You walk.",
    )
    edit_agent(walker.id, move_speed=2)

    updated = next(
        a for a in client.get("/api/state").json()["agents"] if a["id"] == walker.id
    )
    assert updated["move_speed"] == 2


def test_post_create_area_route(client):
    response = client.post(
        "/api/create-area",
        json={
            "area_id": "attic",
            "description": "A dusty attic.",
            "width": 6,
            "height": 4,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "attic" in data["snapshot"]["areas"]
    assert data["snapshot"]["active_area_id"] == "attic"


def test_post_edit_area_route(client):
    client.post(
        "/api/create-area",
        json={"area_id": "cellar", "description": "Old cellar.", "width": 5, "height": 5},
    )
    response = client.post(
        "/api/edit-area",
        json={
            "area_id": "cellar",
            "description": "Damp cellar.",
            "width": 7,
            "height": 7,
        },
    )
    data = response.json()
    assert data["ok"] is True
    block = data["snapshot"]["areas"]["cellar"]
    assert block["area_description"] == "Damp cellar."


def test_post_delete_area_route(client):
    client.post(
        "/api/create-area",
        json={"area_id": "closet", "description": "Empty closet."},
    )
    response = client.post("/api/delete-area", json={"area_id": "closet"})
    data = response.json()
    assert data["ok"] is True
    assert "closet" not in data["snapshot"]["areas"]


def test_post_delete_area_with_agents_rejected(client):
    response = client.post("/api/delete-area", json={"area_id": ROOM})
    assert response.json()["ok"] is False


def test_get_llm_settings_never_returns_api_key(client):
    response = client.get("/api/settings/llm")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "api_key" not in data
    assert "key_configured" in data
    assert "model" in data
    assert data["provider"] in ("openrouter", "featherless")
    assert data["max_input_tokens"] >= 1
    assert 1 <= data["input_warning_percent"] <= 100


def test_put_llm_settings_in_memory(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MAX_INPUT_TOKENS", raising=False)
    monkeypatch.delenv("LLM_INPUT_WARNING_PERCENT", raising=False)
    response = client.put(
        "/api/settings/llm",
        json={
            "provider": "featherless",
            "api_key": "test-key",
            "model": "test/model",
            "max_input_tokens": 16000,
            "input_warning_percent": 85,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["provider"] == "featherless"
    assert data["key_configured"] is True
    assert data["model"] == "test/model"
    assert data["max_input_tokens"] == 16000
    assert data["input_warning_percent"] == 85
    get_resp = client.get("/api/settings/llm")
    get_data = get_resp.json()
    assert get_data["key_configured"] is True
    assert get_data["provider"] == "featherless"
    assert "api_key" not in get_data


def test_prompt_includes_token_budget_fields(client, monkeypatch):
    monkeypatch.setenv("LLM_MAX_INPUT_TOKENS", "32768")
    monkeypatch.setenv("LLM_INPUT_WARNING_PERCENT", "90")
    create_agent(name="Scout", position=(1, 1), personality="curious")
    response = client.get("/api/prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "prompt_tokens" in data
    assert data["max_input_tokens"] == 32768
    assert data["input_warning_percent"] == 90
    assert data["warning_threshold"] == int(32768 * 90 / 100)
    assert "over_warning" in data
    assert "over_limit" in data


def test_turn_refuses_when_prompt_over_max_input_tokens(client, monkeypatch):
    monkeypatch.setenv("LLM_MAX_INPUT_TOKENS", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    create_agent(name="Talker", position=(1, 1), personality="verbose")
    response = client.post("/api/turn", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data.get("over_limit") is True
    assert data["max_input_tokens"] == 1
    assert data["prompt_tokens_estimate"] > 1
    assert "token" in data["message"].lower() or "limit" in data["message"].lower()


def test_session_import_fails_with_unknown_memory_module(client):
    create_agent(
        name="Archivist",
        position=(2, 2),
        personality="x",
        memory_module="recent_turns",
    )
    snapshot = client.get("/api/session/export").json()
    agents = snapshot.get("agents") or []
    assert agents
    agents[0]["memory"] = {
        "module_id": "rolling_summary_custom",
        "module_state": {},
        "looked_at": [],
        "ever_looked": [],
    }

    response = client.post("/api/session/import", json=snapshot)
    assert response.status_code == 400
    detail = str(response.json()["detail"]).lower()
    assert "rolling_summary_custom" in detail
    assert "unsupported" in detail or "unknown" in detail


_LOREBOOK_JSON = """{
  "entries": {
    "0": {
      "uid": 0,
      "key": ["midway"],
      "keysecondary": [],
      "comment": "Midway",
      "content": "The Midway is a megastructure.",
      "constant": true,
      "disable": false,
      "selective": false,
      "selectiveLogic": 0,
      "order": 0
    }
  }
}"""


def test_create_lorebook_api(client):
    response = client.post("/api/lorebooks", json={"name": "Scratch pad"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["lorebook_id"] == "scratch-pad"
    assert data["lorebook"]["entries"] == []

    detail = client.get("/api/lorebooks/scratch-pad").json()
    assert detail["ok"] is True
    assert detail["lorebook"]["name"] == "Scratch pad"


def test_load_demo_lorebook_api(client):
    response = client.post("/api/lorebooks/load-demo")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["lorebook_id"] == "campaign-rpg-engine-demo"
    assert len(data["lorebook"]["entries"]) == 3

    listing = client.get("/api/lorebooks").json()
    ids = {book["id"] for book in listing["lorebooks"]}
    assert "campaign-rpg-engine-demo" in ids


def test_upload_lorebook_and_list(client):
    response = client.post(
        "/api/lorebooks/upload",
        files={"file": ("test.lorebook.json", _LOREBOOK_JSON, "application/json")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    book_id = data["lorebook_id"]

    listing = client.get("/api/lorebooks").json()
    ids = {book["id"] for book in listing["lorebooks"]}
    assert book_id in ids

    detail = client.get(f"/api/lorebooks/{book_id}").json()
    assert detail["ok"] is True
    assert detail["lorebook"]["entries"][0]["content"].startswith("The Midway")


def test_put_lorebook_updates_entry(client):
    client.post(
        "/api/lorebooks/upload",
        files={"file": ("edit-me.lorebook.json", _LOREBOOK_JSON, "application/json")},
    )
    book_id = client.get("/api/lorebooks").json()["lorebooks"][0]["id"]
    book = client.get(f"/api/lorebooks/{book_id}").json()["lorebook"]
    book["entries"][0]["content"] = "Updated lore text."
    book["entries"][0]["enabled"] = False
    response = client.put(f"/api/lorebooks/{book_id}", json=book)
    assert response.status_code == 200
    saved = response.json()["lorebook"]["entries"][0]
    assert saved["content"] == "Updated lore text."
    assert saved["enabled"] is False


def test_put_lorebook_add_and_remove_entries(client):
    client.post(
        "/api/lorebooks/upload",
        files={"file": ("mutable.lorebook.json", _LOREBOOK_JSON, "application/json")},
    )
    book_id = client.get("/api/lorebooks").json()["lorebooks"][0]["id"]
    book = client.get(f"/api/lorebooks/{book_id}").json()["lorebook"]
    assert len(book["entries"]) == 1

    book["entries"].append(
        {
            "uid": 99,
            "enabled": True,
            "constant": False,
            "keys": ["session-only"],
            "keys_secondary": [],
            "selective": False,
            "selective_logic": 0,
            "content": "Custom session lore.",
            "comment": "Session extra",
            "order": 1,
            "ignore_budget": False,
        }
    )
    response = client.put(f"/api/lorebooks/{book_id}", json=book)
    assert response.status_code == 200
    saved = response.json()["lorebook"]
    assert len(saved["entries"]) == 2
    assert saved["entries"][1]["content"] == "Custom session lore."
    downloaded = client.get(f"/api/lorebooks/{book_id}/download").json()
    new_entry = downloaded["entries"]["99"]
    assert new_entry["probability"] == 100
    assert new_entry["depth"] == 4

    book = saved
    book["entries"] = [book["entries"][1]]
    response = client.put(f"/api/lorebooks/{book_id}", json=book)
    assert response.status_code == 200
    saved = response.json()["lorebook"]
    assert len(saved["entries"]) == 1
    assert saved["entries"][0]["comment"] == "Session extra"


_LOREBOOK_WITH_DEFERRED = """{
  "entries": {
    "0": {
      "uid": 0,
      "key": ["midway"],
      "content": "The Midway is a megastructure.",
      "constant": true,
      "disable": false,
      "selective": false,
      "selectiveLogic": 0,
      "order": 0,
      "probability": 100,
      "position": 4
    }
  }
}"""


def test_download_lorebook_st_json(client):
    client.post(
        "/api/lorebooks/upload",
        files={
            "file": ("world.lorebook.json", _LOREBOOK_WITH_DEFERRED, "application/json"),
        },
    )
    book_id = client.get("/api/lorebooks").json()["lorebooks"][0]["id"]
    book = client.get(f"/api/lorebooks/{book_id}").json()["lorebook"]
    book["entries"][0]["content"] = "Edited Midway text."
    book["entries"][0]["enabled"] = False
    client.put(f"/api/lorebooks/{book_id}", json=book)

    response = client.get(f"/api/lorebooks/{book_id}/download")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "").lower()
    payload = response.json()
    entry = payload["entries"]["0"]
    assert entry["content"] == "Edited Midway text."
    assert entry["disable"] is True
    assert entry["constant"] is True
    assert entry["probability"] == 100
    assert entry["position"] == 4
    assert "enabled" not in entry


def test_lorebook_scan_config_api(client):
    listing = client.get("/api/lorebooks/scan-config").json()
    assert listing["ok"] is True
    source_ids = {row["id"] for row in listing["sources"]}
    assert "passive_vision" in source_ids
    assert "memory" in source_ids

    updated = client.put(
        "/api/lorebooks/scan-config",
        json={"memory": False, "passive_vision": True},
    ).json()
    assert updated["ok"] is True
    assert updated["config"]["memory"] is False
    by_id = {row["id"]: row for row in updated["sources"]}
    assert by_id["memory"]["enabled"] is False
    assert by_id["passive_vision"]["enabled"] is True


def test_prompt_preview_includes_lorebook_slot(client):
    client.post(
        "/api/lorebooks/upload",
        files={"file": ("world.lorebook.json", _LOREBOOK_JSON, "application/json")},
    )
    book_id = client.get("/api/lorebooks").json()["lorebooks"][0]["id"]
    base = client.get("/api/prompt-blocks").json()["blocks"]
    blocks = list(base)
    blocks.insert(
        1,
        {
            "type": "slot",
            "name": "lorebook",
            "options": {"lorebook_id": book_id},
        },
    )
    preview = client.post("/api/prompt-blocks/preview", json={"blocks": blocks}).json()
    lore_block = next(b for b in preview["blocks"] if b.get("name") == "lorebook")
    assert "World info:" in lore_block.get("preview", "")


def _create_player_agent(_client, name="Tester"):
    agent = create_agent(
        name=name,
        position=(0, 0),
        personality="Manual tester.",
        is_player=True,
    )
    state = _client.get("/api/state").json()
    return next(item for item in state["agents"] if item["id"] == agent.id)


def test_create_player_agent_in_snapshot(client):
    agent = _create_player_agent(client)
    assert agent["is_player"] is True
    assert agent["id"].startswith("agent_")


def test_post_manual_turn_moves_player(client):
    agent = _create_player_agent(client)
    client.post("/api/active-agent", json={"name_or_id": agent["id"]})

    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Walk east.",
                "move": "2,0",
                "action": "none",
            },
        },
    )
    data = response.json()
    assert data["ok"] is True
    assert data["manual_turn"] is True
    assert data["snapshot"]["session_turn"] == 1
    updated = next(item for item in data["snapshot"]["agents"] if item["id"] == agent["id"])
    assert updated["position"] == [2, 0]


def test_post_turn_rejects_player_agent(client):
    agent = _create_player_agent(client)
    client.post("/api/active-agent", json={"name_or_id": agent["id"]})

    response = client.post("/api/turn", json={})
    data = response.json()
    assert data["ok"] is False
    assert "player" in data["message"].lower()


def test_post_manual_turn_rejects_llm_agent(client, monkeypatch):
    monkeypatch.setattr(
        "backend.turn_runner.get_compound_turn",
        _fake_compound_response,
    )
    response = client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Nope.",
                "action": "none",
            },
        },
    )
    data = response.json()
    assert data["ok"] is False
    assert "player" in data["message"].lower()


def test_post_turn_with_agent_id_keeps_active_agent(client, monkeypatch):
    monkeypatch.setattr(
        "backend.turn_runner.get_compound_turn",
        _fake_compound_response,
    )
    player = _create_player_agent(client, name="Hero")
    npc = create_agent(
        name="Goblin",
        position=(1, 0),
        personality="Grumpy.",
        is_player=False,
    )
    client.post("/api/active-agent", json={"name_or_id": player["id"]})

    response = client.post("/api/turn", json={"agent_id": npc.id})
    data = response.json()
    assert data["ok"] is True
    assert data["snapshot"]["active_agent_id"] == player["id"]
    assert data["snapshot"]["session_turn"] == 1


def test_post_manual_turn_with_agent_id_keeps_active_agent(client):
    player = _create_player_agent(client, name="Hero")
    guide = create_agent(
        name="Guide",
        position=(0, 1),
        personality="Helpful.",
        is_player=False,
    )
    client.post("/api/active-agent", json={"name_or_id": guide.id})

    response = client.post(
        "/api/turn/manual",
        json={
            "agent_id": player["id"],
            "compound_turn": {
                "reasoning": "Step forward.",
                "move": "1,0",
                "action": "none",
            },
        },
    )
    data = response.json()
    assert data["ok"] is True
    assert data["snapshot"]["active_agent_id"] == guide.id
    updated = next(item for item in data["snapshot"]["agents"] if item["id"] == player["id"])
    assert updated["position"] == [1, 0]
