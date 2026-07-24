"""LLM + hosting settings routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.hosting import get_hosting_settings, set_public_base_url
from backend.schemas import HostingSettingsRequest, LlmSettingsRequest
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
        concurrent_llm_calls=body.concurrent_llm_calls,
    )


@router.get("/api/settings/hosting")
def get_hosting_settings_route() -> dict[str, object]:
    return get_hosting_settings()


@router.put("/api/settings/hosting")
def put_hosting_settings_route(body: HostingSettingsRequest) -> dict[str, object]:
    return set_public_base_url(body.public_base_url)
