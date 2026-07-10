"""Typed ``Session`` helpers for API tests (no CLI command strings)."""

from __future__ import annotations

from backend.session_store import get_session_store
from realm_fabric import ObjectAction, Session


def get_session() -> Session:
    return get_session_store().session


def create_object(**kwargs):
    result = get_session().create_object(**kwargs)
    assert result.ok, result.message
    assert result.object is not None
    return result.object


def create_agent(**kwargs):
    result = get_session().create_agent(**kwargs)
    assert result.ok, result.message
    assert result.agent is not None
    return result.agent


def edit_object(object_id: str, **kwargs):
    result = get_session().edit_object(object_id, **kwargs)
    assert result.ok, result.message
    return result


def edit_agent(agent_id: str, **kwargs):
    result = get_session().edit_agent(agent_id, **kwargs)
    assert result.ok, result.message
    return result


def add_object_action(object_id: str, action: ObjectAction):
    result = get_session().add_object_action(object_id, action)
    assert result.ok, result.message
    return result
