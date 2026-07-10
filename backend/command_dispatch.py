"""Dispatch stepper-style command lines without ``Session.run_command``."""

from __future__ import annotations

from realm_fabric import (
    CommandResult,
    Session,
    create_area_from_args,
    delete_area_by_id,
    edit_area_from_args,
    format_agents_list,
    format_full_list,
    format_handlers_list,
    format_memory_modules_list,
    format_objects_list,
    parse_area_event_arg,
)


def dispatch_command(session: Session, line: str) -> CommandResult:
    """
    Parse and run a stepper-style command line using typed ``Session`` APIs.

    Same command vocabulary as the legacy CLI stepper; does not run compound turns.
    """
    line = line.strip()
    if not line:
        return CommandResult(ok=False, message="Empty command.")

    parts = line.split(None, 1)
    cmd = parts[0].lower().replace("-", "_")
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "create_object":
        result = session.create_object_from_command(arg)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "edit_object":
        result = session.edit_object_from_command(arg)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "delete_object":
        result = session.delete_object(arg.strip())
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "create_agent":
        result = session.create_agent_from_command(arg)
        return CommandResult(ok=result.ok, message=result.message)
    if cmd == "edit_agent":
        result = session.edit_agent_from_command(arg)
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
            lines.append(
                f"  {area_id}{marker} — {agent_count} agent(s), {obj_count} object(s)"
            )
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
