"""Initiative turn-order tests (Studio 1.7.1)."""

from __future__ import annotations

import pytest
from backend.app import create_app
from backend.initiative import INITIATIVE_KEY
from backend.session_store import get_session_store, reset_session_store
from fastapi.testclient import TestClient
from tests.world_helpers import create_agent, get_session


@pytest.fixture(autouse=True)
def _fresh_session_store():
    reset_session_store()
    yield
    reset_session_store()


@pytest.fixture
def client():
    return TestClient(create_app())


def _hero() -> str:
    return create_agent(
        name="Hero",
        position=(1, 1),
        personality="brave",
        is_player=True,
    ).id


def _guard() -> str:
    return create_agent(
        name="Guard",
        position=(2, 2),
        personality="stern",
        is_player=False,
    ).id


def test_enable_initiative_syncs_active_agent(client):
    hero = _hero()
    guard = _guard()
    response = client.put(
        "/api/initiative",
        json={"enabled": True, "order": [guard, hero]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["initiative"]["enabled"] is True
    assert data["initiative"]["current_agent_id"] == guard
    assert get_session().active_agent_id == guard


def test_enable_initiative_requires_order(client):
    _hero()
    response = client.put("/api/initiative", json={"enabled": True, "order": []})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False


def test_player_turn_rejected_when_not_current(client):
    hero = _hero()
    guard = _guard()
    client.put("/api/initiative", json={"enabled": True, "order": [guard, hero]})
    token = client.post("/api/seats", json={"agent_id": hero}).json()["token"]
    response = client.post(
        "/api/player/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={"compound_turn": {"reasoning": "go", "action": "none", "move": "1,1"}},
    )
    assert response.status_code == 403


def test_player_turn_accepted_when_current(client):
    hero = _hero()
    guard = _guard()
    client.put("/api/initiative", json={"enabled": True, "order": [hero, guard]})
    token = client.post("/api/seats", json={"agent_id": hero}).json()["token"]
    response = client.post(
        "/api/player/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={"compound_turn": {"reasoning": "go", "action": "none", "move": "1,1"}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    state = client.get("/api/initiative").json()["initiative"]
    assert state["current_agent_id"] == guard


def test_initiative_next_advances_without_turn(client):
    hero = _hero()
    guard = _guard()
    client.put("/api/initiative", json={"enabled": True, "order": [hero, guard]})
    response = client.post("/api/initiative/next")
    assert response.status_code == 200
    assert response.json()["initiative"]["current_agent_id"] == guard


def test_initiative_order_in_state_snapshot(client):
    hero = _hero()
    guard = _guard()
    client.put("/api/initiative", json={"enabled": True, "order": [hero, guard]})
    state = client.get("/api/state").json()
    initiative = state.get("initiative") or {}
    assert initiative.get("enabled") is True
    assert initiative.get("order") == [hero, guard]


def test_initiative_survives_export_import(client):
    hero = _hero()
    guard = _guard()
    client.put("/api/initiative", json={"enabled": True, "order": [hero, guard]})
    exported = client.get("/api/session/export")
    assert exported.status_code == 200
    save = exported.json()
    reset_session_store()
    imported = client.post("/api/session/import", json=save)
    assert imported.status_code == 200
    initiative = client.get("/api/initiative").json()["initiative"]
    assert initiative["enabled"] is True
    assert initiative["order"] == [hero, guard]
    ext = get_session().extensions.get(INITIATIVE_KEY) or {}
    assert ext.get("enabled") is True


def test_disabled_initiative_allows_any_player_turn(client):
    hero = _hero()
    _guard()
    token = client.post("/api/seats", json={"agent_id": hero}).json()["token"]
    response = client.post(
        "/api/player/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={"compound_turn": {"reasoning": "go", "action": "none", "move": "1,1"}},
    )
    assert response.status_code == 200


def test_gm_turn_rejected_out_of_initiative_slot(client):
    hero = _hero()
    guard = _guard()
    client.put("/api/initiative", json={"enabled": True, "order": [guard, hero]})
    response = client.post(
        "/api/turn/manual",
        json={
            "agent_id": hero,
            "compound_turn": {"reasoning": "go", "action": "none", "move": "1,1"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "turn" in data["message"].lower()
