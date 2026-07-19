"""Plugin platform API tests (1.2.0)."""

from pathlib import Path

import pytest
from backend.app import create_app
from backend.plugin_registry import clear_plugin_registry_for_tests
from backend.plugin_upload import load_all_plugins
from backend.session_store import reset_session_store
from campaign_rpg_engine import clear_event_listeners_for_tests, clear_turn_verbs_for_tests
from campaign_rpg_engine.prompt_slots.registry import clear_prompt_slots_for_tests
from fastapi.testclient import TestClient

_FIXTURES_PLUGINS = Path(__file__).resolve().parent / "fixtures" / "plugins"


@pytest.fixture(autouse=True)
def _fresh_plugin_state():
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()
    load_all_plugins(extra_dirs=[_FIXTURES_PLUGINS])
    yield
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_plugins_catalog_lists_hello_plugin(client):
    response = client.get("/api/plugins")
    assert response.status_code == 200
    data = response.json()
    ids = {p["id"] for p in data["plugins"]}
    assert "hello_plugin" in ids


def test_enable_disable_plugin(client):
    enable = client.post("/api/plugins/hello_plugin/enable")
    assert enable.status_code == 200
    assert enable.json()["ok"] is True

    catalog = client.get("/api/plugins").json()
    hello = next(p for p in catalog["plugins"] if p["id"] == "hello_plugin")
    assert hello["enabled"] is True

    state = client.get("/api/state?include_private=1").json()
    assert state["extensions"]["hello_plugin"]["greeting"] == "hello from plugin"

    disable = client.post("/api/plugins/hello_plugin/disable")
    assert disable.status_code == 200


def test_plugin_panel_and_action(client):
    client.post("/api/plugins/hello_plugin/enable")
    panel = client.get("/api/plugins/hello_plugin/panel")
    assert panel.status_code == 200
    body = panel.json()
    assert body["panel"]["title"] == "Hello Plugin"

    action = client.post(
        "/api/plugins/hello_plugin/action",
        json={"action_id": "ping", "params": {}},
    )
    assert action.status_code == 200
    assert action.json()["message"] == "pong"


def test_plugin_state_round_trips_in_session_export(client):
    client.post("/api/plugins/hello_plugin/enable")
    export = client.get("/api/session/export")
    save = export.json()
    assert save["extensions"]["_studio_plugins"]["enabled"] == ["hello_plugin"]

    client.post("/api/plugins/hello_plugin/disable")
    client.post("/api/session/import", json=save)
    catalog = client.get("/api/plugins").json()
    hello = next(p for p in catalog["plugins"] if p["id"] == "hello_plugin")
    assert hello["enabled"] is True


def test_plugins_tab_markup(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="tab-plugins"' in html
    assert 'id="plugins-tab-panel"' in html


def test_upload_plugin_py(client, tmp_path, monkeypatch):
    from backend import plugin_upload as pu

    monkeypatch.setattr(pu, "CUSTOM_PLUGINS_DIR", tmp_path)
    source = (_FIXTURES_PLUGINS / "hello_plugin" / "__init__.py").read_text(encoding="utf-8")
    # Upload under a distinct id to avoid duplicate with fixture load
    source = source.replace('PLUGIN_ID = "hello_plugin"', 'PLUGIN_ID = "uploaded_hello"')
    files = {"file": ("uploaded_hello.py", source, "text/x-python")}
    response = client.post("/api/plugins/upload", files=files)
    assert response.status_code == 200
    assert response.json()["plugin_id"] == "uploaded_hello"
