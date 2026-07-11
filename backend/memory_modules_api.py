"""Memory module catalog for campaign-rpg-studio agent creation (V0.4.6)."""

from __future__ import annotations

from typing import Any

from campaign_rpg_engine import (
    DEFAULT_CHAR_BUDGET,
    DEFAULT_MAX_SUMMARY_CHARS,
    DEFAULT_SUMMARY_INTERVAL,
    DEFAULT_SUMMARY_TAIL,
    DEFAULT_WINDOW,
    MAX_CHAR_BUDGET,
    MAX_MAX_SUMMARY_CHARS,
    MAX_WINDOW,
    MIN_CHAR_BUDGET,
    MIN_MAX_SUMMARY_CHARS,
    MIN_SUMMARY_INTERVAL,
    MIN_SUMMARY_TAIL,
    MIN_WINDOW,
    default_module_id,
    get_custom_module_metadata,
    loaded_module_ids,
)


def _option(
    flag: str,
    label: str,
    *,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "flag": flag,
        "label": label,
        "default": default,
        "min": minimum,
    }
    if maximum is not None:
        data["max"] = maximum
    return data


def get_memory_modules_catalog() -> dict[str, Any]:
    """Structured catalog for create-agent memory module UI (loaded modules only)."""
    modules: list[dict[str, Any]] = []
    for module_id in loaded_module_ids():
        if module_id == "recent_turns":
            modules.append(
                {
                    "id": module_id,
                    "label": "Recent turns",
                    "description": (
                        "Last N own turns plus witnessed other-agent actions (engine default)"
                    ),
                    "options": [
                        _option(
                            "memory-window",
                            "Turn window",
                            default=DEFAULT_WINDOW,
                            minimum=MIN_WINDOW,
                            maximum=MAX_WINDOW,
                        ),
                    ],
                }
            )
        elif module_id == "salient_turns":
            modules.append(
                {
                    "id": module_id,
                    "label": "Salient turns",
                    "description": (
                        "Salience-weighted retention; Memory section capped by character budget"
                    ),
                    "options": [
                        _option(
                            "memory-budget",
                            "Character budget",
                            default=DEFAULT_CHAR_BUDGET,
                            minimum=MIN_CHAR_BUDGET,
                            maximum=MAX_CHAR_BUDGET,
                        ),
                    ],
                }
            )
        elif module_id == "rolling_summary":
            modules.append(
                {
                    "id": module_id,
                    "label": "Rolling summary",
                    "description": (
                        "Verbatim recent turns plus periodic LLM summary consolidation"
                    ),
                    "options": [
                        _option(
                            "memory-summary-interval",
                            "Summary interval (turns)",
                            default=DEFAULT_SUMMARY_INTERVAL,
                            minimum=MIN_SUMMARY_INTERVAL,
                        ),
                        _option(
                            "memory-summary-max",
                            "Max summary chars",
                            default=DEFAULT_MAX_SUMMARY_CHARS,
                            minimum=MIN_MAX_SUMMARY_CHARS,
                            maximum=MAX_MAX_SUMMARY_CHARS,
                        ),
                        _option(
                            "memory-summary-tail",
                            "Detail tail after summary",
                            default=DEFAULT_SUMMARY_TAIL,
                            minimum=MIN_SUMMARY_TAIL,
                        ),
                    ],
                }
            )
        else:
            meta = get_custom_module_metadata(module_id)
            if meta is not None:
                modules.append(
                    {
                        "id": module_id,
                        "label": meta.label,
                        "description": meta.description,
                        "options": list(meta.create_agent_options),
                        "custom": True,
                        "filename": meta.filename,
                    }
                )
            else:
                modules.append(
                    {
                        "id": module_id,
                        "label": module_id.replace("_", " ").title(),
                        "description": "",
                        "options": [],
                        "custom": True,
                    }
                )

    custom_modules = [
        {
            "id": m["id"],
            "label": m.get("label", m["id"]),
            "filename": m.get("filename", ""),
        }
        for m in modules
        if m.get("custom")
    ]

    return {
        "ok": True,
        "default_id": default_module_id(),
        "modules": modules,
        "custom_modules": custom_modules,
    }
