"""Scene decoration API tests (V1.3.0)."""

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.session_store import reset_session_store
from tests.world_helpers import get_session


@pytest.fixture(autouse=True)
def _fresh_session_store():
    reset_session_store()
    yield
    reset_session_store()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_create_sprite_and_background(client):
    bg = client.post(
        "/api/decorations",
        json={
            "kind": "background",
            "image": "assets/stone.png",
            "repeat": "repeat",
        },
    )
    assert bg.status_code == 200
    bg_body = bg.json()
    assert bg_body["ok"] is True
    assert bg_body["decoration"]["kind"] == "background"

    sprite = client.post(
        "/api/decorations",
        json={
            "kind": "sprite",
            "image": "assets/tree.png",
            "x": 10,
            "y": 20,
            "width": 64,
            "height": 96,
        },
    )
    assert sprite.status_code == 200
    sprite_body = sprite.json()
    assert sprite_body["ok"] is True
    decor_id = sprite_body["decoration"]["id"]

    state = client.get("/api/state").json()
    room = state["areas"][state["active_area_id"]]
    assert len(room["decorations"]) == 2

    session = get_session()
    area = session.areas[state["active_area_id"]]
    assert len(area.decorations) == 2


def test_update_reorder_and_delete_sprite(client):
    created = client.post(
        "/api/decorations",
        json={
            "kind": "sprite",
            "image": "assets/a.png",
            "x": 0,
            "y": 0,
            "width": 32,
            "height": 32,
            "decoration_id": "decor_test_a",
        },
    ).json()
    assert created["ok"] is True

    client.post(
        "/api/decorations",
        json={
            "kind": "sprite",
            "image": "assets/b.png",
            "x": 0,
            "y": 0,
            "width": 32,
            "height": 32,
            "decoration_id": "decor_test_b",
        },
    )

    updated = client.put(
        "/api/decorations",
        json={
            "decoration_id": "decor_test_a",
            "x": 48,
            "y": 64,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["decoration"]["x"] == 48

    reordered = client.post(
        "/api/decorations/reorder",
        json={"decoration_id": "decor_test_a", "direction": "up"},
    )
    assert reordered.status_code == 200
    assert reordered.json()["ok"] is True

    deleted = client.request(
        "DELETE",
        "/api/decorations",
        json={"decoration_id": "decor_test_a"},
    )
    assert deleted.status_code == 200
    state = deleted.json()["snapshot"]
    decorations = state["areas"][state["active_area_id"]]["decorations"]
    assert all(d["id"] != "decor_test_a" for d in decorations)


def test_background_replaces_previous(client):
    client.post(
        "/api/decorations",
        json={"kind": "background", "image": "assets/old.png"},
    )
    client.post(
        "/api/decorations",
        json={"kind": "background", "image": "assets/new.png"},
    )
    state = client.get("/api/state").json()
    decorations = state["areas"][state["active_area_id"]]["decorations"]
    backgrounds = [d for d in decorations if d["kind"] == "background"]
    assert len(backgrounds) == 1
    assert backgrounds[0]["image"] == "assets/new.png"


def test_upload_decoration_asset(client, tmp_path, monkeypatch):
    from backend import decoration_assets_api as assets_api

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    monkeypatch.setattr(assets_api, "ASSETS_DIR", assets_dir)

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    response = client.post(
        "/api/decoration-assets/upload",
        files={"file": ("tree.png", png, "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["path"] == "assets/tree.png"
    assert body.get("reused") is False
    assert (assets_dir / "tree.png").is_file()

    again = client.post(
        "/api/decoration-assets/upload",
        files={"file": ("tree.png", png, "image/png")},
    )
    assert again.status_code == 200
    reused = again.json()
    assert reused["path"] == "assets/tree.png"
    assert reused.get("reused") is True
    assert list(assets_dir.glob("tree*.png")) == [assets_dir / "tree.png"]


def test_update_decoration_negative_xy(client):
    client.post(
        "/api/decorations",
        json={
            "kind": "sprite",
            "image": "assets/a.png",
            "x": 0,
            "y": 0,
            "width": 32,
            "height": 32,
            "decoration_id": "decor_neg",
        },
    )
    updated = client.put(
        "/api/decorations",
        json={
            "decoration_id": "decor_neg",
            "x": -48,
            "y": -32,
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["decoration"]["x"] == -48
    assert body["decoration"]["y"] == -32
