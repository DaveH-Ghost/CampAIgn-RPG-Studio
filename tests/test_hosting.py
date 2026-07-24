"""Hosting / public join URL tests (Studio 1.7.4)."""

from __future__ import annotations

import pytest
from backend.app import create_app
from backend.hosting import reset_hosting_for_tests, resolve_join_base, set_public_base_url
from backend.session_store import reset_session_store
from fastapi.testclient import TestClient
from tests.world_helpers import create_agent


@pytest.fixture(autouse=True)
def _fresh():
    reset_session_store()
    reset_hosting_for_tests()
    yield
    reset_session_store()
    reset_hosting_for_tests()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_resolve_join_base_prefers_public_url():
    set_public_base_url("https://campaign.example.com")
    base, err = resolve_join_base("http://127.0.0.1:8765/")
    assert err is None
    assert base == "https://campaign.example.com"


def test_resolve_join_base_rejects_all_interfaces_without_public():
    base, err = resolve_join_base("http://0.0.0.0:8765/")
    assert base is None
    assert err and "Public base URL" in err


def test_hosting_settings_roundtrip(client):
    get0 = client.get("/api/settings/hosting")
    assert get0.status_code == 200
    assert get0.json()["ok"] is True
    assert get0.json()["listen_host"] == "127.0.0.1"

    bad = client.put("/api/settings/hosting", json={"public_base_url": "not-a-url"})
    assert bad.status_code == 200
    assert bad.json()["ok"] is False

    ok = client.put(
        "/api/settings/hosting",
        json={"public_base_url": "https://play.example.com"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["ok"] is True
    assert body["public_base_url"] == "https://play.example.com"

    clear = client.put("/api/settings/hosting", json={"public_base_url": ""})
    assert clear.status_code == 200
    assert clear.json()["public_base_url"] == ""


def test_create_seat_uses_public_base_url(client):
    agent = create_agent(
        name="Hero",
        position=(1, 1),
        personality="brave",
        is_player=True,
    )
    client.put(
        "/api/settings/hosting",
        json={"public_base_url": "https://campaign.example.com"},
    )
    mint = client.post("/api/seats", json={"agent_id": agent.id})
    assert mint.status_code == 200
    data = mint.json()
    assert data["join_url"].startswith("https://campaign.example.com/play/generic/?seat=")


def test_health_includes_hosting_fields(client):
    health = client.get("/api/health").json()
    assert "listen_host" in health
    assert "listen_port" in health
    assert "public_base_url" in health
