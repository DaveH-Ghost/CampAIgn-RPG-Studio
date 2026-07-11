"""In-memory LLM settings for campaign-rpg-studio (V0.4.6)."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"


def get_llm_settings() -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return {
        "ok": True,
        "model": model,
        "key_configured": bool(key),
    }


def put_llm_settings(
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    if api_key is not None:
        cleaned = api_key.strip()
        if cleaned:
            os.environ["OPENROUTER_API_KEY"] = cleaned
        elif "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]

    if model is not None:
        cleaned_model = model.strip()
        if cleaned_model:
            os.environ["OPENROUTER_MODEL"] = cleaned_model
        elif "OPENROUTER_MODEL" in os.environ:
            del os.environ["OPENROUTER_MODEL"]

    return get_llm_settings()
