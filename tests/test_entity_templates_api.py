"""Entity template library API tests."""

from pathlib import Path

import pytest
from backend import entity_templates_api as templates_api
from backend.app import create_app
from backend.plugin_registry import clear_plugin_registry_for_tests
from backend.plugin_upload import load_all_plugins
from backend.session_store import reset_session_store
from campaign_rpg_engine import (
    clear_event_listeners_for_tests,
    clear_turn_verbs_for_tests,
)
from campaign_rpg_engine.prompt_slots.registry import clear_prompt_slots_for_tests
from fastapi.testclient import TestClient
from reference_handlers import register_reference_handlers
from tests.world_helpers import create_agent, create_object, get_session

_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


@pytest.fixture(autouse=True)
def _fresh_template_api_state(tmp_path, monkeypatch):
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()
    register_reference_handlers()
    load_all_plugins(extra_dirs=[_PLUGINS_DIR])
    monkeypatch.setattr(templates_api, "ENTITY_TEMPLATES_DIR", tmp_path / "entity_templates")
    yield
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_save_and_spawn_object_template(client):
    ball = create_object(
        name="Coffee Mug",
        position=(1, 1),
        passive_description="Warm.",
        blocks_movement=False,
    )
    add = client.post(
        "/api/entity-templates/save-from-entity",
        json={
            "kind": "object",
            "entity_id": ball.id,
            "filename": "coffee-mug.json",
        },
    )
    assert add.status_code == 200
    assert add.json()["ok"] is True

    listed = client.get("/api/entity-templates").json()
    assert any(t["id"] == "coffee-mug" for t in listed["templates"])

    session = get_session()
    assert session.area.get_object_by_id(ball.id) is not None

    spawn = client.post(
        "/api/entity-templates/coffee-mug/spawn",
        json={"position": [3, 3]},
    )
    assert spawn.status_code == 200
    body = spawn.json()
    assert body["ok"] is True
    assert body["kind"] == "object"
    assert body["entity_id"] != ball.id
    assert session.area.get_object_by_id(body["entity_id"]) is not None


def test_save_agent_with_memory_and_spawn(client):
    agent = create_agent(
        name="Shopkeeper",
        position=(0, 1),
        personality="Friendly.",
        is_player=False,
    )
    session = get_session()
    live = session.get_agent(agent.id)
    assert live is not None
    live.memory.mark_looked_at("agent_player_01")

    save = client.post(
        "/api/entity-templates/save-from-entity",
        json={
            "kind": "agent",
            "entity_id": agent.id,
            "filename": "shopkeeper.json",
            "include_memory": True,
        },
    )
    assert save.status_code == 200

    get_tpl = client.get("/api/entity-templates/shopkeeper").json()
    assert get_tpl["template"]["include_memory"] is True
    assert "memory" in get_tpl["template"]

    spawn = client.post(
        "/api/entity-templates/shopkeeper/spawn",
        json={"position": [2, 2]},
    )
    assert spawn.status_code == 200
    new_id = spawn.json()["entity_id"]
    placed = session.get_agent(new_id)
    assert placed is not None
    assert placed.id != agent.id
    assert "agent_player_01" in placed.memory.looked_at


def test_spawn_object_template_twice_new_ids(client):
    obj = create_object(name="Table", position=(0, 0), passive_description=".")
    client.post(
        "/api/entity-templates/save-from-entity",
        json={"kind": "object", "entity_id": obj.id, "filename": "table.json"},
    )
    first = client.post("/api/entity-templates/table/spawn", json={"position": [1, 1]}).json()
    second = client.post("/api/entity-templates/table/spawn", json={"position": [2, 2]}).json()
    assert first["ok"] and second["ok"]
    assert first["entity_id"] != second["entity_id"]


def test_export_entity_template_download(client):
    obj = create_object(name="Door", position=(0, 0), passive_description="Heavy.")
    res = client.post(
        "/api/entity-templates/export-from-entity",
        json={"kind": "object", "entity_id": obj.id, "filename": "door.json"},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    assert 'filename="door.json"' in res.headers.get("content-disposition", "")
    payload = res.json()
    assert payload["kind"] == "object"
    assert payload["name"] == "Door"
    assert "id" not in payload


def test_spawn_from_template_file_body(client):
    obj = create_object(name="Crate", position=(1, 1), passive_description="Wooden.")
    exported = client.post(
        "/api/entity-templates/export-from-entity",
        json={"kind": "object", "entity_id": obj.id, "filename": "crate.json"},
    ).json()
    spawn = client.post(
        "/api/entity-templates/spawn-from-template",
        json={"template": exported, "position": [4, 4]},
    )
    assert spawn.status_code == 200
    body = spawn.json()
    assert body["ok"] is True
    assert body["entity_id"] != obj.id
    assert get_session().area.get_object_by_id(body["entity_id"]) is not None


def test_import_entity_template_file(client):
    obj = create_object(name="Barrel", position=(0, 0), passive_description=".")
    exported = client.post(
        "/api/entity-templates/export-from-entity",
        json={"kind": "object", "entity_id": obj.id, "filename": "barrel.json"},
    ).json()
    imported = client.post(
        "/api/entity-templates/import",
        json={"filename": "barrel.json", "template": exported},
    )
    assert imported.status_code == 200
    assert imported.json()["ok"] is True

    listed = client.get("/api/entity-templates").json()
    assert any(t["id"] == "barrel" for t in listed["templates"])

    deleted = client.delete("/api/entity-templates/barrel")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True
