"""Area template library API tests."""

from pathlib import Path

import pytest
from backend import area_templates_api as templates_api
from backend.app import create_app
from backend.plugin_registry import clear_plugin_registry_for_tests
from backend.plugin_upload import load_all_plugins
from backend.session_store import reset_session_store
from campaign_rpg_engine import clear_event_listeners_for_tests, clear_turn_verbs_for_tests
from campaign_rpg_engine.prompt_slots.registry import clear_prompt_slots_for_tests
from fastapi.testclient import TestClient
from reference_handlers import register_reference_handlers
from tests.world_helpers import create_object, get_session

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
    monkeypatch.setattr(templates_api, "AREA_TEMPLATES_DIR", tmp_path / "area_templates")
    yield
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_save_and_spawn_area_template_new_area(client):
    session = get_session()
    area_id = session.active_area_id
    create_object(name="Bench", position=(2, 2), passive_description="Wood.")

    save = client.post(
        "/api/area-templates/save-from-area",
        json={
            "area_id": area_id,
            "filename": "tavern-room.json",
            "name": "Tavern Room",
        },
    )
    assert save.status_code == 200
    assert save.json()["ok"] is True

    listed = client.get("/api/area-templates").json()
    assert any(t["id"] == "tavern-room" for t in listed["templates"])

    spawn = client.post(
        "/api/area-templates/tavern-room/spawn",
        json={"area_id": "tavern_copy", "mode": "new"},
    )
    assert spawn.status_code == 200
    body = spawn.json()
    assert body["ok"] is True
    assert body["area_id"] == "tavern_copy"
    assert "tavern_copy" in get_session().areas
    assert any(obj.name == "Bench" for obj in get_session().areas["tavern_copy"].get_objects())


def test_spawn_area_template_replace_mode(client):
    session = get_session()
    area_id = session.active_area_id
    create_object(name="Marker", position=(1, 1), passive_description=".")

    save = client.post(
        "/api/area-templates/save-from-area",
        json={"area_id": area_id, "filename": "starter.json"},
    )
    assert save.status_code == 200

    created = session.create_area(area_id="sandbox", description="Sandbox.", width=5, height=5)
    assert created.ok
    session.set_active_area("sandbox")
    create_object(name="Temporary", position=(0, 0), passive_description=".")

    spawn = client.post(
        "/api/area-templates/starter/spawn",
        json={"area_id": "sandbox", "mode": "replace"},
    )
    assert spawn.status_code == 200
    body = spawn.json()
    assert body["ok"] is True
    sandbox = get_session().areas["sandbox"]
    assert not any(obj.name == "Temporary" for obj in sandbox.get_objects())


def test_export_area_template_download(client):
    session = get_session()
    area_id = session.active_area_id
    create_object(name="Statue", position=(0, 0), passive_description="Stone.")

    res = client.post(
        "/api/area-templates/export-from-area",
        json={"area_id": area_id, "filename": "statue-room.json"},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    payload = res.json()
    assert payload["kind"] == "area"
    assert any(obj["name"] == "Statue" for obj in payload.get("objects", []))


def test_import_and_delete_area_template(client):
    session = get_session()
    exported = client.post(
        "/api/area-templates/export-from-area",
        json={"area_id": session.active_area_id, "filename": "imported.json"},
    ).json()

    imported = client.post(
        "/api/area-templates/import",
        json={"filename": "imported.json", "template": exported},
    )
    assert imported.status_code == 200
    assert imported.json()["ok"] is True

    deleted = client.delete("/api/area-templates/imported")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True
