"""
Example custom memory module — port of built-in rolling_summary (V0.4.6).

Demonstrates the custom module loading contract without new behavior.
"""

from __future__ import annotations

from typing import Any

from realm_fabric import (
    DEFAULT_MAX_SUMMARY_CHARS,
    DEFAULT_SUMMARY_INTERVAL,
    DEFAULT_SUMMARY_TAIL,
    MAX_MAX_SUMMARY_CHARS,
    MIN_MAX_SUMMARY_CHARS,
    MIN_SUMMARY_INTERVAL,
    MIN_SUMMARY_TAIL,
    MemoryModule,
    RollingSummaryModule,
)

MODULE_ID = "rolling_summary_custom"
MODULE_LABEL = "Rolling summary (custom)"
MODULE_DESCRIPTION = (
    "Example custom module: verbatim detail plus periodic LLM summary consolidation "
    "(same behavior as built-in rolling_summary)."
)

CREATE_AGENT_OPTIONS: list[dict[str, Any]] = [
    {
        "flag": "memory-summary-interval",
        "label": "Summary interval (turns)",
        "default": DEFAULT_SUMMARY_INTERVAL,
        "min": MIN_SUMMARY_INTERVAL,
    },
    {
        "flag": "memory-summary-max",
        "label": "Max summary chars",
        "default": DEFAULT_MAX_SUMMARY_CHARS,
        "min": MIN_MAX_SUMMARY_CHARS,
        "max": MAX_MAX_SUMMARY_CHARS,
    },
    {
        "flag": "memory-summary-tail",
        "label": "Detail tail after summary",
        "default": DEFAULT_SUMMARY_TAIL,
        "min": MIN_SUMMARY_TAIL,
    },
]


class RollingSummaryCustomModule(RollingSummaryModule):
    module_id: str = MODULE_ID


def create_module(**config: Any) -> MemoryModule:
    return RollingSummaryCustomModule(
        module_id=MODULE_ID,
        summary_interval=int(config.get("summary_interval", DEFAULT_SUMMARY_INTERVAL)),
        max_summary_chars=int(config.get("max_summary_chars", DEFAULT_MAX_SUMMARY_CHARS)),
        summary_tail=int(config.get("summary_tail", DEFAULT_SUMMARY_TAIL)),
        background_consolidation=bool(config.get("background_consolidation", True)),
    )
