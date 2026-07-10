"""Snapshot normalization for multi-area engine (V0.4.0c1–c2)."""

from backend.snapshot_compat import flatten_snapshot_for_ui, normalize_state_snapshot


def test_normalize_multi_area_snapshot():
    raw = {
        "session_turn": 2,
        "active_agent_id": "agent_01",
        "active_area_id": "room",
        "areas": {
            "room": {
                "grid": {"min_x": 0, "max_x": 4, "min_y": 0, "max_y": 4},
                "objects": [{"id": "obj_ball_01"}],
                "recent_events": [],
            },
            "hall": {
                "grid": {"min_x": 0, "max_x": 4, "min_y": 0, "max_y": 4},
                "recent_events": [],
            },
        },
        "agents": [{"id": "agent_01", "area_id": "room"}],
    }
    norm = normalize_state_snapshot(raw)
    assert isinstance(norm["areas"]["hall"]["objects"], list)
    assert norm["areas"]["hall"]["objects"] == []
    assert "grid" not in norm


def test_flatten_hall_missing_objects_key():
    raw = {
        "session_turn": 0,
        "active_agent_id": "agent_01",
        "active_area_id": "hall",
        "areas": {
            "hall": {"grid": {"min_x": 0, "max_x": 4, "min_y": 0, "max_y": 4}},
        },
        "agents": [],
    }
    flat = flatten_snapshot_for_ui(raw)
    assert flat["objects"] == []


def test_ensure_flat_arrays_on_legacy_shape():
    partial = {"session_turn": 0, "active_agent_id": "agent_01", "grid": {"min_x": 0}}
    norm = normalize_state_snapshot(partial)
    assert "areas" in norm
