"""skill_check interaction handler."""

from __future__ import annotations

import sys

from campaign_rpg_engine.action_outcome import ActionOutcome
from campaign_rpg_engine.interact_templates import InteractTemplateContext, format_interact_template
from campaign_rpg_engine.interaction_handlers import (
    collect_prefixed_params,
    is_handler_registered,
    run_named_handler,
    validate_handler_params,
)

dice = sys.modules["studio_plugin_skills.dice"]
sheet = sys.modules["studio_plugin_skills.sheet"]
state = sys.modules["studio_plugin_skills.state"]

HANDLER_ID = "skill_check"

_OWN_PARAMS = frozenset(
    {
        "stat",
        "skill",
        "dc",
        "fail_result",
        "fail_passive",
        "pass_handler",
        "fail_handler",
    }
)
_FAIL_NEST_SKIP = frozenset({"fail_handler", "fail_result", "fail_passive"})
_PASS_NEST_SKIP = frozenset({"pass_handler"})

PARAM_FIELDS = [
    {
        "name": "stat",
        "label": "Stat",
        "type": "select",
        "required": True,
        "default": "STR",
        "options": [
            {"value": name, "label": name} for name in ("CON", "STR", "DEX", "WIS", "INT", "CHM")
        ],
    },
    {
        "name": "dc",
        "label": "DC (difficulty)",
        "type": "number",
        "required": True,
        "default": "10",
    },
    {
        "name": "skill",
        "label": "Skill (optional, e.g. athletics)",
        "type": "text",
        "placeholder": "Leave blank for bare stat check",
    },
    {
        "name": "fail_result",
        "label": "Fail result (agent sees)",
        "type": "textarea",
        "placeholder": "Default: You fail the check.",
        "template_vars": True,
    },
    {
        "name": "fail_passive",
        "label": "Fail passive / area event",
        "type": "textarea",
        "placeholder": "Default: {actor} fails.",
        "template_vars": True,
    },
    {
        "name": "pass_handler",
        "label": "On pass handler",
        "type": "handler_ref",
        "param_prefix": "pass_",
        "exclude_handlers": ["skill_check"],
        "summary_key": "pass",
    },
    {
        "name": "fail_handler",
        "label": "On fail handler",
        "type": "handler_ref",
        "param_prefix": "fail_",
        "exclude_handlers": ["skill_check"],
        "summary_key": "fail",
    },
]

SUMMARY_TEMPLATE = "skill_check {stat} DC {dc}"

INTERACT_TEMPLATE_VARS = (
    {
        "name": "raw_roll",
        "description": "Natural d20 result before modifiers (skill_check only)",
    },
    {
        "name": "roll_bonus",
        "description": "Total bonus added to the roll — signed "
        "(stat modifier + skill, if any; skill_check only)",
    },
    {
        "name": "modified_roll",
        "description": "Final check total: raw_roll + roll_bonus (skill_check only)",
    },
    {
        "name": "dc_target",
        "description": "Difficulty class this check was rolled against (skill_check only)",
    },
)


def _is_allowed_param_key(key: str) -> bool:
    if key in _OWN_PARAMS:
        return True
    return key.startswith("pass_") or key.startswith("fail_")


def validate_skill_check_params(params: dict[str, str]) -> str | None:
    if "stat" not in params or not str(params.get("stat", "")).strip():
        return "skill_check requires param 'stat' (CON, STR, DEX, WIS, INT, or CHM)."
    stat = str(params["stat"]).strip().upper()
    if stat not in dice.STAT_NAMES:
        known = ", ".join(dice.STAT_NAMES)
        return f"Unknown stat {stat!r}. Known: {known}."
    if "dc" not in params or not str(params.get("dc", "")).strip():
        return "skill_check requires param 'dc' (integer difficulty)."
    try:
        int(params["dc"])
    except (TypeError, ValueError):
        return "skill_check param 'dc' must be an integer."

    unknown = sorted(key for key in params if not _is_allowed_param_key(key))
    if unknown:
        return f"Unknown skill_check params: {', '.join(unknown)}."

    for branch, key in (("pass", "pass_handler"), ("fail", "fail_handler")):
        follow_id = str(params.get(key, "")).strip()
        if not follow_id:
            continue
        if follow_id == HANDLER_ID:
            return f"skill_check {branch}_handler cannot be skill_check."
        nested = collect_prefixed_params(
            params,
            f"{branch}_",
            skip_keys=_PASS_NEST_SKIP if branch == "pass" else _FAIL_NEST_SKIP,
        )
        err = validate_handler_params(follow_id, nested)
        if err:
            return f"skill_check {branch}_handler: {err}"
        if not is_handler_registered(follow_id):
            return f"Unknown {branch}_handler '{follow_id}'."
    return None


def _template_ctx(agent, obj, area_id: str) -> InteractTemplateContext:
    pos = agent.position
    return InteractTemplateContext(
        actor=agent.name,
        object_name=obj.name,
        object_start=obj.position,
        object_end=obj.position,
        actor_start=pos,
        actor_end=pos,
        object_start_area=area_id,
        object_end_area=area_id,
        actor_start_area=area_id,
        actor_end_area=area_id,
    )


def _roll_replacements(outcome: dict) -> dict[str, str]:
    bonus = int(outcome["modifier"]) + int(outcome["skill_bonus"])
    return {
        "raw_roll": str(outcome["roll"]),
        "roll_bonus": f"{bonus:+d}",
        "modified_roll": str(outcome["total"]),
        "dc_target": str(outcome["dc"]),
    }


def format_with_roll_vars(template: str, ctx: InteractTemplateContext, outcome: dict) -> str:
    """Substitute core interact placeholders, then skills roll placeholders."""
    text = format_interact_template(template, ctx)
    for key, value in _roll_replacements(outcome).items():
        text = text.replace("{" + key + "}", value)
    return text


def _run_followup(session, area, agent, obj, action, params: dict[str, str], *, passed: bool):
    branch = "pass" if passed else "fail"
    follow_id = str(params.get(f"{branch}_handler", "")).strip()
    if not follow_id:
        return None
    nested = collect_prefixed_params(
        params,
        f"{branch}_",
        skip_keys=_PASS_NEST_SKIP if passed else _FAIL_NEST_SKIP,
    )
    return run_named_handler(
        session,
        area,
        agent,
        obj,
        follow_id,
        nested,
        source_action=action,
    )


def skill_check(session, area, agent, obj, action) -> ActionOutcome | str | None:
    if session is None:
        return "skill_check requires a session."
    if not state.plugin_enabled(session):
        return "Skills plugin is not enabled."

    params = dict(action.handler_params or {})
    err = validate_skill_check_params(params)
    if err:
        return err

    agent_sheet = sheet.get_sheet(agent)
    if agent_sheet.get("parse_error"):
        return str(agent_sheet["parse_error"])

    outcome = dice.resolve_check(
        stats=agent_sheet["stats"],
        skills=agent_sheet["skills"],
        stat=str(params["stat"]),
        skill=str(params.get("skill", "")).strip() or None,
        dc=int(params["dc"]),
    )
    follow = _run_followup(session, area, agent, obj, action, params, passed=outcome["passed"])
    if isinstance(follow, str):
        return follow

    area_id = session.agent_area.get(agent.id, "") or ""
    ctx = _template_ctx(agent, obj, area_id)

    if outcome["passed"]:
        return ActionOutcome(
            result=format_with_roll_vars(action.result, ctx, outcome),
            passive_result=format_with_roll_vars(action.passive_result, ctx, outcome),
        )

    fail_result = str(params.get("fail_result") or "").strip() or (
        f"You fail the {outcome['stat']} check."
    )
    fail_passive = str(params.get("fail_passive") or "").strip() or (
        "{actor} fails a check."
    )
    return ActionOutcome(
        result=format_with_roll_vars(fail_result, ctx, outcome),
        passive_result=format_with_roll_vars(fail_passive, ctx, outcome),
    )
