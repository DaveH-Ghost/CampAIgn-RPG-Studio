"""In-memory LLM settings for campaign-rpg-studio (1.7.4)."""

from __future__ import annotations

import os
from typing import Any

from campaign_rpg_engine import (
    DEFAULT_INPUT_WARNING_PERCENT,
    DEFAULT_MAX_INPUT_TOKENS,
    concurrent_llm_calls_enabled,
    get_input_warning_percent,
    get_llm_provider,
    get_max_input_tokens,
    set_concurrent_llm_calls,
)
from campaign_rpg_engine.llm.client import (
    DEFAULT_FEATHERLESS_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    PROVIDER_FEATHERLESS,
    PROVIDER_OPENROUTER,
    resolve_llm_model,
)

VALID_PROVIDERS = frozenset({PROVIDER_OPENROUTER, PROVIDER_FEATHERLESS})


def get_llm_settings() -> dict[str, Any]:
    provider = get_llm_provider()
    if provider == PROVIDER_FEATHERLESS:
        key = os.environ.get("FEATHERLESS_API_KEY", "").strip()
    else:
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = resolve_llm_model()
    return {
        "ok": True,
        "provider": provider,
        "model": model,
        "key_configured": bool(key),
        "max_input_tokens": get_max_input_tokens(),
        "input_warning_percent": get_input_warning_percent(),
        "concurrent_llm_calls": concurrent_llm_calls_enabled(),
        "defaults": {
            "openrouter_model": DEFAULT_OPENROUTER_MODEL,
            "featherless_model": DEFAULT_FEATHERLESS_MODEL,
            "max_input_tokens": DEFAULT_MAX_INPUT_TOKENS,
            "input_warning_percent": DEFAULT_INPUT_WARNING_PERCENT,
            "concurrent_llm_calls": True,
        },
    }


def put_llm_settings(
    *,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    max_input_tokens: int | None = None,
    input_warning_percent: int | None = None,
    concurrent_llm_calls: bool | None = None,
) -> dict[str, Any]:
    if provider is not None:
        cleaned = provider.strip().lower()
        if cleaned not in VALID_PROVIDERS:
            return {
                "ok": False,
                "message": f"provider must be openrouter or featherless (got {provider!r}).",
            }
        os.environ["LLM_PROVIDER"] = cleaned

    active = get_llm_provider()
    key_env = "FEATHERLESS_API_KEY" if active == PROVIDER_FEATHERLESS else "OPENROUTER_API_KEY"
    model_env = "FEATHERLESS_MODEL" if active == PROVIDER_FEATHERLESS else "OPENROUTER_MODEL"

    if api_key is not None:
        cleaned = api_key.strip()
        if cleaned:
            os.environ[key_env] = cleaned
        elif key_env in os.environ:
            del os.environ[key_env]

    if model is not None:
        cleaned_model = model.strip()
        if cleaned_model:
            os.environ[model_env] = cleaned_model
        elif model_env in os.environ:
            del os.environ[model_env]

    if max_input_tokens is not None:
        if int(max_input_tokens) < 1:
            return {"ok": False, "message": "max_input_tokens must be at least 1."}
        os.environ["LLM_MAX_INPUT_TOKENS"] = str(int(max_input_tokens))

    if input_warning_percent is not None:
        pct = int(input_warning_percent)
        if pct < 1 or pct > 100:
            return {
                "ok": False,
                "message": "input_warning_percent must be between 1 and 100.",
            }
        os.environ["LLM_INPUT_WARNING_PERCENT"] = str(pct)

    if concurrent_llm_calls is not None:
        set_concurrent_llm_calls(bool(concurrent_llm_calls))

    return get_llm_settings()
