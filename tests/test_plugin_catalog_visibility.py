"""Plugin catalog visibility vs session enablement."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.plugin_registry import clear_plugin_registry_for_tests
from backend.plugin_upload import load_all_plugins
from backend.session_store import reset_session_store
from campaign_rpg_engine import clear_event_listeners_for_tests, clear_turn_verbs_for_tests
from campaign_rpg_engine.prompt_slots.registry import clear_prompt_slots_for_tests
from reference_handlers import register_reference_handlers

_PLUGINS = Path(__file__).resolve().parent.parent / "plugins"


@pytest.fixture(autouse=True)
def _fresh_plugins():
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()
    register_reference_handlers()
    load_all_plugins(extra_dirs=[_PLUGINS])
    yield
    reset_session_store()
    clear_plugin_registry_for_tests()
    clear_event_listeners_for_tests()
    clear_turn_verbs_for_tests()
    clear_prompt_slots_for_tests()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_prompt_slots_hide_disabled_plugin(client):
    slots = client.get("/api/prompt-slots").json()["slots"]
    assert "inventory" not in {item["name"] for item in slots}

    client.post("/api/plugins/inventory/enable")
    slots = client.get("/api/prompt-slots").json()["slots"]
    assert "inventory" in {item["name"] for item in slots}

    client.post("/api/plugins/inventory/disable")
    slots = client.get("/api/prompt-slots").json()["slots"]
    assert "inventory" not in {item["name"] for item in slots}
