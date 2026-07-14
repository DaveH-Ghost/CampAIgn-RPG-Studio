"""Skills plugin — stats/skills in agent private_data and skill_check interacts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_PLUGIN_DIR = Path(__file__).resolve().parent


def _import_plugin_module(relative_name: str):
    qualified = f"studio_plugin_skills.{relative_name}"
    if qualified in sys.modules:
        return sys.modules[qualified]
    path = _PLUGIN_DIR / f"{relative_name}.py"
    spec = importlib.util.spec_from_file_location(qualified, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load skills plugin module {relative_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


state = _import_plugin_module("state")
dice = _import_plugin_module("dice")
sheet = _import_plugin_module("sheet")
handlers = _import_plugin_module("handlers")

PLUGIN_ID = state.PLUGIN_ID
PLUGIN_LABEL = "Skills"
PLUGIN_VERSION = "1"
PLUGIN_DESCRIPTION = (
    "Agent stats (CON/STR/DEX/WIS/INT/CHM) and named skills in private_data. "
    "Attach handler skill_check to object actions for d20 checks "
    "(success uses action result/passive; fail uses fail_result/fail_passive params)."
)


def _format_prompt(session, agent_id: str) -> str:
    agent = session.get_agent(agent_id)
    if agent is None:
        return ""
    data = sheet.get_sheet(agent)
    lines = ["Your abilities:"]
    for name in dice.STAT_NAMES:
        score = data["stats"][name]
        mod = dice.stat_modifier(score)
        lines.append(f"- {name} {score} ({mod:+d})")
    skills = data["skills"]
    if skills:
        lines.append("Skills:")
        for name in sorted(skills):
            lines.append(f"- {name} {skills[name]}")
    else:
        lines.append("Skills: (none)")
    if data.get("parse_error"):
        lines.append(f"(Note: {data['parse_error']})")
    return "\n".join(lines)


def _prompt_slot(session, agent, area, ctx_prompt, options):
    del area, ctx_prompt, options
    if not state.plugin_enabled(session):
        return ""
    return _format_prompt(session, agent.id)


def _build_panel(session):
    agent = session.get_active_agent()
    if agent is None:
        return {
            "title": "Skills",
            "description": PLUGIN_DESCRIPTION,
            "sections": [{"type": "text", "content": "No active agent."}],
        }
    data = sheet.get_sheet(agent)
    status = (
        "Stored in private_data."
        if data.get("initialized")
        else "Not stored yet — checks still use defaults (all 10); click Initialize to write JSON."
    )
    sections: list[dict[str, Any]] = [
        {
            "type": "text",
            "content": (
                f"Stats for {agent.name}. {status} "
                "Edit via right-click → Edit agent → Advanced → private_data "
                "(JSON key skills_plugin)."
            ),
        },
        {
            "type": "key_value_list",
            "items": [
                {
                    "key": name,
                    "value": f"{data['stats'][name]} ({dice.stat_modifier(data['stats'][name]):+d})",
                }
                for name in dice.STAT_NAMES
            ],
        },
    ]
    if data["skills"]:
        sections.append(
            {
                "type": "key_value_list",
                "items": [
                    {"key": name, "value": str(level)}
                    for name, level in sorted(data["skills"].items())
                ],
            }
        )
    else:
        sections.append({"type": "text", "content": "No skills yet."})

    if data.get("parse_error"):
        sections.append({"type": "text", "content": str(data["parse_error"])})

    if not data.get("initialized") and not data.get("parse_error"):
        sections.append(
            {
                "type": "button",
                "id": "init_stats",
                "label": "Initialize stats in private_data",
            }
        )

    sections.append(
        {
            "type": "text",
            "content": (
                "private_data example (skills are name → level integers):\n"
                '{\n'
                '  "skills_plugin": {\n'
                '    "stats": { "CON": 10, "STR": 10, "DEX": 14, '
                '"WIS": 10, "INT": 10, "CHM": 10 },\n'
                '    "skills": { "lockpicking": 3, "persuasion": 1 }\n'
                "  }\n"
                "}"
            ),
        }
    )

    sections.append(
        {
            "type": "text",
            "content": (
                "Object action: handler skill_check with params stat, dc, optional skill, "
                "fail_result, fail_passive, pass_handler, fail_handler "
                "(nested follow-up params use pass_/fail_ prefixes). "
                "Success uses the action's result/passive_result; both support roll "
                "placeholders {raw_roll}, {roll_bonus}, {modified_roll}, {dc_target}."
            ),
        }
    )
    return {
        "title": "Skills",
        "description": PLUGIN_DESCRIPTION,
        "sections": sections,
    }


def _init_stats_action(session, params: dict[str, Any]) -> dict[str, Any]:
    del params
    if not state.plugin_enabled(session):
        return {"ok": False, "message": "Skills plugin is not enabled."}
    agent = session.get_active_agent()
    if agent is None:
        return {"ok": False, "message": "No active agent."}
    return sheet.init_default_sheet(session, agent)


def register(ctx):
    ctx.register_handler(
        handlers.HANDLER_ID,
        handlers.skill_check,
        description="d20 check using agent stats/skills; fail returns ActionOutcome",
        validate_params=handlers.validate_skill_check_params,
        param_fields=handlers.PARAM_FIELDS,
        summary_template=handlers.SUMMARY_TEMPLATE,
    )
    ctx.register_interact_template_vars(list(handlers.INTERACT_TEMPLATE_VARS))
    ctx.register_prompt_slot(
        "skills",
        _prompt_slot,
        description="Active agent stats and skills",
    )
    ctx.set_panel_builder(_build_panel)
    ctx.register_panel_action("init_stats", _init_stats_action)
