"""Turn undo via full session checkpoints (Studio)."""

import pytest
from backend.app import create_app
from backend.session_store import get_session_store, reset_session_store
from campaign_rpg_engine import AgentCompoundTurn, LLMParseError, LLMResponse
from fastapi.testclient import TestClient
from tests.world_helpers import create_agent


@pytest.fixture(autouse=True)
def _fresh_session_store():
    reset_session_store()
    yield
    reset_session_store()


@pytest.fixture
def client():
    return TestClient(create_app())


def _create_player(client, name="Tester"):
    agent = create_agent(
        name=name,
        position=(0, 0),
        personality="Manual tester.",
        is_player=True,
    )
    client.post("/api/active-agent", json={"name_or_id": agent.id})
    return agent


def _manual_move(client, *, move="2,0"):
    return client.post(
        "/api/turn/manual",
        json={
            "compound_turn": {
                "reasoning": "Walk.",
                "move": move,
                "action": "none",
            },
        },
    )


def test_undo_status_empty_initially(client):
    response = client.get("/api/turn/undo")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["can_undo"] is False
    assert data["undo_remaining"] == 0


def test_manual_turn_then_undo_restores_position_and_turn(client):
    agent = _create_player(client)
    moved = _manual_move(client, move="2,0")
    assert moved.json()["ok"] is True
    assert moved.json()["undo_remaining"] == 1
    assert moved.json()["can_undo"] is True
    assert moved.json()["snapshot"]["session_turn"] == 1
    updated = next(item for item in moved.json()["snapshot"]["agents"] if item["id"] == agent.id)
    assert updated["position"] == [2, 0]

    undone = client.post("/api/turn/undo")
    data = undone.json()
    assert data["ok"] is True
    assert data["can_undo"] is False
    assert data["undo_remaining"] == 0
    assert data["snapshot"]["session_turn"] == 0
    restored = next(item for item in data["snapshot"]["agents"] if item["id"] == agent.id)
    assert restored["position"] == [0, 0]


def test_failed_llm_turn_does_not_push_undo(client, monkeypatch):
    create_agent(
        name="Npc",
        position=(1, 1),
        personality="An NPC.",
        is_player=False,
    )
    client.post("/api/active-agent", json={"name_or_id": "Npc"})

    def fail_llm(_prompt):
        raise RuntimeError("OPENROUTER_API_KEY not found.")

    monkeypatch.setattr("backend.turn_runner.get_compound_turn", fail_llm)
    response = client.post("/api/turn", json={})
    assert response.json()["ok"] is False

    status = client.get("/api/turn/undo").json()
    assert status["can_undo"] is False
    assert status["undo_remaining"] == 0


def test_failed_llm_parse_does_not_push_undo(client, monkeypatch):
    create_agent(
        name="Npc",
        position=(1, 1),
        personality="An NPC.",
        is_player=False,
    )
    client.post("/api/active-agent", json={"name_or_id": "Npc"})

    def bad_parse(_prompt):
        raise LLMParseError("bad json", raw_response='{"reasoning": "broken"')

    monkeypatch.setattr("backend.turn_runner.get_compound_turn", bad_parse)
    response = client.post("/api/turn", json={})
    data = response.json()
    assert data["ok"] is False
    assert data["llm_response"] == '{"reasoning": "broken"'
    assert data.get("prompt")
    assert client.get("/api/turn/undo").json()["undo_remaining"] == 0


def test_successful_llm_turn_pushes_undo(client, monkeypatch):
    npc = create_agent(
        name="Npc",
        position=(1, 1),
        personality="An NPC.",
        is_player=False,
    )
    client.post("/api/active-agent", json={"name_or_id": npc.id})

    monkeypatch.setattr(
        "backend.turn_runner.get_compound_turn",
        lambda _prompt: LLMResponse(
            parsed=AgentCompoundTurn(
                reasoning="Stay put.",
                action="none",
            ),
            raw_response="{}",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
        ),
    )
    response = client.post("/api/turn", json={})
    data = response.json()
    assert data["ok"] is True
    assert data["undo_remaining"] == 1

    undone = client.post("/api/turn/undo").json()
    assert undone["ok"] is True
    assert undone["snapshot"]["session_turn"] == 0


def test_command_clears_undo_stack(client):
    _create_player(client)
    moved = _manual_move(client)
    assert moved.json()["undo_remaining"] == 1

    cmd = client.post("/api/command", json={"line": 'create-object name "Cup" at 0,1'})
    assert cmd.json()["ok"] is True
    assert cmd.json()["can_undo"] is False
    assert cmd.json()["undo_remaining"] == 0
    assert client.get("/api/turn/undo").json()["undo_remaining"] == 0


def test_import_clears_undo_stack(client):
    _create_player(client)
    moved = _manual_move(client)
    assert moved.json()["undo_remaining"] == 1

    save = get_session_store().export_session()
    imported = client.post("/api/session/import", json=save)
    assert imported.status_code == 200
    assert imported.json()["ok"] is True
    assert client.get("/api/turn/undo").json()["undo_remaining"] == 0


def test_undo_when_empty_returns_error(client):
    response = client.post("/api/turn/undo")
    data = response.json()
    assert data["ok"] is False
    assert "nothing to undo" in data["message"].lower()
