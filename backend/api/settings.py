"""LLM settings routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import LlmSettingsRequest
from backend.settings_api import get_llm_settings, put_llm_settings

router = APIRouter()


@router.get("/api/settings/llm")
def get_llm_settings_route() -> dict[str, object]:
    return get_llm_settings()


@router.put("/api/settings/llm")
def put_llm_settings_route(body: LlmSettingsRequest) -> dict[str, object]:
    return put_llm_settings(
        provider=body.provider,
        api_key=body.api_key,
        model=body.model,
        max_input_tokens=body.max_input_tokens,
        input_warning_percent=body.input_warning_percent,
    )
