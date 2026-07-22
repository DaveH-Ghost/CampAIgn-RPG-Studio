"""Player seat + /api/player/* tests (Studio 1.7.0)."""

from __future__ import annotations

import pytest
from backend.app import create_app
from backend.session_store import reset_session_store
from fastapi.testclient import TestClient
from tests.world_helpers import add_object_action, create_agent, create_object, edit_object


@pytest.fixture(autouse=True)
def _fresh_session_store():
    reset_session_store()
    yield
    reset_session_store()


@pytest.fixture
def client():
    return TestClient(create_app())


def _player(client) -> str:
    agent = create_agent(
        name="Hero",
        position=(1, 1),
        personality="brave",
        is_player=True,
    )
    return agent.id


def test_create_seat_rejects_npc(client):
    npc = create_agent(
        name="Guard",
        position=(2, 2),
        personality="stern",
        is_player=False,
    )
    response = client.post("/api/seats", json={"agent_id": npc.id})
    assert response.status_code == 400


def test_create_seat_and_player_view(client):
    agent_id = _player(client)
    hidden = create_object(name="Secret", position=(0, 0), passive_description="hidden")
    edit_object(hidden.id, hidden=True)
    visible = create_object(name="Ball", position=(2, 1), passive_description="a ball")

    mint = client.post("/api/seats", json={"agent_id": agent_id})
    assert mint.status_code == 200
    data = mint.json()
    assert data["ok"] is True
    assert data["token"]
    assert "/play/generic/?seat=" in data["join_url"]
    token = data["token"]

    bad = client.get("/api/player/view")
    assert bad.status_code == 401

    view = client.get("/api/player/view", headers={"Authorization": f"Bearer {token}"})
    assert view.status_code == 200
    body = view.json()
    assert body["ok"] is True
    assert body["agent_id"] == agent_id
    object_ids = {o["id"] for o in body["objects"]}
    assert visible.id in object_ids
    assert hidden.id not in object_ids
    assert "personality" not in str(body)
    assert body.get("passive_vision") is not None
    assert "grid" in body
    assert "decorations" in body


def test_player_turn_and_query_seat(client):
    agent_id = _player(client)
    token = client.post("/api/seats", json={"agent_id": agent_id}).json()["token"]

    result = client.post(
        f"/api/player/turn?seat={token}",
        json={
            "compound_turn": {
                "reasoning": "test",
                "action": "none",
                "move": "2,2",
            }
        },
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["ok"] is True
    assert payload["view"]["agent_id"] == agent_id
    me = client.get("/api/player/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["agent_id"] == agent_id


def test_expired_or_bogus_token(client):
    response = client.get(
        "/api/player/view",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_revoke_seat(client):
    agent_id = _player(client)
    token = client.post("/api/seats", json={"agent_id": agent_id}).json()["token"]
    assert client.delete(f"/api/seats/{token}").json()["revoked"] is True
    assert (
        client.get("/api/player/view", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )


def test_player_history_includes_own_results(client):
    agent_id = _player(client)
    create_object(name="Ball", position=(2, 1), passive_description="a ball")
    token = client.post("/api/seats", json={"agent_id": agent_id}).json()["token"]
    client.post(
        "/api/player/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={"compound_turn": {"reasoning": "go", "action": "none", "move": "2,1"}},
    )
    view = client.get(
        "/api/player/view",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    texts = [e["text"] for e in view.get("history") or []]
    assert texts, "expected history entries after a move"
    assert any(e.get("source") == "you" for e in view["history"])


def test_player_history_groups_compound_turn(client):
    agent_id = _player(client)
    create_object(
        name="Ball",
        position=(2, 1),
        passive_description="a slightly worn ceramic ball",
    )
    token = client.post("/api/seats", json={"agent_id": agent_id}).json()["token"]
    client.post(
        "/api/player/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "compound_turn": {
                "reasoning": "compound",
                "action": "emote",
                "verb": "waved",
                "move": "2,1",
                "look": "obj_ball_01",
                "say": "hello",
            }
        },
    )
    view = client.get(
        "/api/player/view",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    yours = [e for e in view.get("history") or [] if e.get("source") == "you"]
    assert len(yours) == 1
    entry = yours[0]
    assert entry.get("kind") == "compound"
    assert len(entry.get("kinds") or []) >= 2
    text = entry["text"]
    assert "\n" in text
    assert "hello" in text.lower() or "said" in text.lower()
    assert "emote" in text.lower() or "waved" in text.lower()
    assert "looked" in text.lower() or "ball" in text.lower()


def test_player_history_groups_witnessed_compound_turn(client):
    """NPC say+interact should appear as one witness card, not two."""
    from campaign_rpg_engine import AgentCompoundTurn, ObjectAction
    from tests.world_helpers import get_session

    player_id = _player(client)
    npc = create_agent(
        name="Scout",
        position=(2, 2),
        personality="curious",
        is_player=False,
    )
    ball = create_object(
        name="Ball",
        position=(2, 2),
        passive_description="a ceramic ball",
    )
    add_object_action(
        ball.id,
        ObjectAction(
            name="kick",
            range=1,
            result="You kick the {object}.",
            passive_result="{actor} kicks the {object}.",
        ),
    )
    token = client.post("/api/seats", json={"agent_id": player_id}).json()["token"]
    result = get_session().run_compound_turn(
        AgentCompoundTurn(
            reasoning="curious",
            action="interact",
            target=ball.id,
            verb="kick",
            say="A ceramic ball... curious.",
        ),
        agent_id=npc.id,
    )
    assert result.ok, result.message
    view = client.get(
        "/api/player/view",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    witnessed = [
        e
        for e in view.get("history") or []
        if e.get("source") == "witness" and e.get("actor_id") == npc.id
    ]
    assert len(witnessed) == 1, witnessed
    entry = witnessed[0]
    assert entry.get("kind") == "compound"
    text = entry["text"].lower()
    assert "\n" in entry["text"]
    assert "curious" in text or "says" in text or "said" in text
    assert "kick" in text


def test_session_events_notify_subscribers():
    from backend.session_events import (
        publish_session_changed,
        reset_session_events_for_tests,
        subscribe,
        unsubscribe,
        wait_revision,
    )

    reset_session_events_for_tests()
    sub = subscribe()
    try:
        primed = wait_revision(sub, 0.5)
        assert primed is not None
        publish_session_changed()
        nxt = wait_revision(sub, 0.5)
        assert nxt is not None
        assert nxt >= primed
    finally:
        unsubscribe(sub)


def test_session_stream_route_registered(client):
    paths = set(client.app.openapi()["paths"])
    assert "/api/session/stream" in paths
    assert "/api/player/stream" in paths


def test_player_view_can_act_when_initiative_current(client):
    hero = _player(client)
    npc = create_agent(
        name="Guard",
        position=(2, 2),
        personality="stern",
        is_player=False,
    )
    client.put(
        "/api/initiative",
        json={"enabled": True, "order": [npc.id, hero]},
    )
    token = client.post("/api/seats", json={"agent_id": hero}).json()["token"]
    view = client.get(
        "/api/player/view",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert view.get("can_act") is False
    assert view.get("wait_reason")
    assert view.get("initiative_current", {}).get("agent_id") == npc.id

    client.post("/api/initiative/next")
    view2 = client.get(
        "/api/player/view",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert view2.get("can_act") is True


def test_player_view_includes_hp_when_set(client):
    import json

    for pid in ("inventory", "skills", "combat"):
        assert client.post(f"/api/plugins/{pid}/enable").json()["ok"] is True
    agent_id = _player(client)
    from backend.session_store import get_session_store

    agent = get_session_store().session.get_agent(agent_id)
    agent.private_data = json.dumps({"combat_plugin": {"hp": 12, "max_hp": 18}})
    token = client.post("/api/seats", json={"agent_id": agent_id}).json()["token"]
    view = client.get("/api/player/view", headers={"Authorization": f"Bearer {token}"}).json()
    assert view["hp"] == 12
    assert view["max_hp"] == 18
    assert len(view["stats"]) == 6
    assert view["stats"][0]["name"] == "CON"
    assert "skills" in view


def test_player_assist_merges_equip_and_hides_combat_attack(client):
    import json

    for pid in ("inventory", "skills", "combat"):
        assert client.post(f"/api/plugins/{pid}/enable").json()["ok"] is True

    agent_id = _player(client)
    client.post("/api/active-agent", json={"name_or_id": agent_id})

    sword = {
        "item_id": "obj_sword_1",
        "name": "Sword",
        "private_data": json.dumps(
            {
                "combat_plugin": {
                    "slot": "weapon",
                    "range": 1,
                    "attack_stat": "STR",
                    "accuracy_bonus": 0,
                    "damage": "1d8",
                    "req": {},
                }
            }
        ),
        "actions": {
            "swing": {
                "kind": "interact",
                "range": 1,
                "handler_id": "combat_attack",
                "handler_params": {},
                "result": "hit",
                "passive_result": "hits",
                "enabled": True,
            },
            "polish": {
                "kind": "interact",
                "range": 0,
                "handler_id": "inventory_consume",
                "handler_params": {},
                "result": "You polish the blade.",
                "passive_result": "polishes a blade.",
                "enabled": True,
            },
        },
    }
    from backend.session_store import get_session_store

    session = get_session_store().session
    inv = session.get_extension("inventory") or {"by_agent": {}}
    inv.setdefault("by_agent", {})[agent_id] = [sword]
    session.set_extension("inventory", inv)

    token = client.post("/api/seats", json={"agent_id": agent_id}).json()["token"]
    view = client.get("/api/player/view", headers={"Authorization": f"Bearer {token}"}).json()
    item_rows = [r for r in view["assist"] if r["id"] == "obj_sword_1"]
    assert len(item_rows) == 1
    verbs = item_rows[0]["verbs"]
    assert "equip" in verbs
    assert "unequip" in verbs
    assert "drop" in verbs
    assert "give" in verbs
    assert "show" in verbs
    assert "polish" in verbs
    assert "swing" not in verbs


def test_social_candidates_include_pathable_agents(client):
    agent_id = _player(client)
    # Hero at (1,1); Dummy at (1,4) is distance 3 — outside social range 1.
    dummy = create_agent(name="Dummy", position=(1, 4), personality="x")
    from backend.session_store import get_session_store

    session = get_session_store().session
    hero = session.get_agent(agent_id)
    hero.move_speed = 2

    token = client.post("/api/seats", json={"agent_id": agent_id}).json()["token"]
    view = client.get("/api/player/view", headers={"Authorization": f"Bearer {token}"}).json()
    ids = {c["id"] for c in view["social_candidates"]}
    # move_speed 2 + social 1 = reach 3 → Dummy at dist 3 is included
    assert dummy.id in ids

    hero.move_speed = 1
    view2 = client.get("/api/player/view", headers={"Authorization": f"Bearer {token}"}).json()
    ids2 = {c["id"] for c in view2["social_candidates"]}
    assert dummy.id not in ids2

    hero.move_speed = None
    view3 = client.get("/api/player/view", headers={"Authorization": f"Bearer {token}"}).json()
    ids3 = {c["id"] for c in view3["social_candidates"]}
    assert dummy.id in ids3
