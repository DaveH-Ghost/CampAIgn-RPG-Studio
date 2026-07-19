"""Dispatch stepper-style command lines (CampAIgn-RPG-Studio owned string layer)."""

from __future__ import annotations

from dataclasses import dataclass

from campaign_rpg_engine import Session, delete_area_by_id, format_agents_list, format_full_list
from campaign_rpg_engine.area_edit import (
    create_agent_from_args,
    create_area_from_args,
    create_object_from_args,
    edit_agent_for_session,
    edit_area_from_args,
    edit_object_for_session,
    format_objects_list,
)
from campaign_rpg_engine.area_event import parse_area_event_arg
from campaign_rpg_engine.interaction_handlers import format_handlers_list
from campaign_rpg_engine.memory_modules.registry import format_memory_modules_list


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    message: str


def dispatch_command(session: Session, line: str) -> CommandResult:
    """
    Parse and run a stepper-style command line using engine helpers.

    Same command vocabulary as the legacy CLI stepper; does not run compound turns.
    """
    line = line.strip()
    if not line:
        return CommandResult(ok=False, message="Empty command.")

    parts = line.split(None, 1)
    cmd = parts[0].lower().replace("-", "_")
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "create_object":
        obj, message = create_object_from_args(session.area, arg)
        return CommandResult(ok=obj is not None, message=message)
    if cmd == "edit_object":
        message = edit_object_for_session(session, arg)
        ok = not message.startswith("Error") and not message.startswith("Unknown")
        return CommandResult(ok=ok, message=message)
    if cmd == "delete_object":
        result = session.delete_object(arg.strip())
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "create_agent":
        agent, message = create_agent_from_args(session.area, arg)
        if agent is not None:
            session._register_agent(agent)
        return CommandResult(ok=agent is not None, message=message)
    if cmd == "edit_agent":
        result = edit_agent_for_session(session, arg)
        if result.ok and result.agent is not None and result.old_name_lower:
            session._rename_agent_in_index(result.old_name_lower, result.agent)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "delete_agent":
        result = session.delete_agent(arg.strip())
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "objects":
        return CommandResult(ok=True, message=format_objects_list(session.area))
    if cmd == "agents":
        return CommandResult(
            ok=True,
            message=format_agents_list(session.area, session.get_active_agent()),
        )
    if cmd == "list":
        return CommandResult(
            ok=True,
            message=format_full_list(session.area, session.get_active_agent()),
        )
    if cmd in {"handlers", "effects"}:
        return CommandResult(ok=True, message=format_handlers_list())
    if cmd == "memory_modules":
        return CommandResult(ok=True, message=format_memory_modules_list())
    if cmd == "emit_event":
        text = parse_area_event_arg(arg)
        if not text:
            return CommandResult(
                ok=False,
                message='Usage: emit-event "Event description."',
            )
        result = session.emit_area_event(text)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "active_area":
        area_id = arg.strip()
        if not area_id:
            known = ", ".join(sorted(session.areas))
            return CommandResult(
                ok=False,
                message=f"Usage: active-area <area_id>  (known: {known})",
            )
        result = session.set_active_area(area_id)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "areas":
        lines = ["Areas:"]
        for area_id in sorted(session.areas):
            marker = " *" if area_id == session.active_area_id else ""
            agent_count = len(session.areas[area_id].agents)
            obj_count = len(session.areas[area_id].get_objects())
            lines.append(f"  {area_id}{marker} — {agent_count} agent(s), {obj_count} object(s)")
        return CommandResult(ok=True, message="\n".join(lines))
    if cmd == "create_area":
        result = create_area_from_args(session, arg)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "edit_area":
        result = edit_area_from_args(session, arg)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "delete_area":
        result = delete_area_by_id(session, arg.strip())
        return CommandResult(ok=result.ok, message=result.message)

    return CommandResult(ok=False, message=f"Unknown command: {parts[0]!r}")
