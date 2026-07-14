"""Tests du router LLM : fallback Gemini vers Mistral, echec total, parsing des reponses."""

import httpx
import pytest
import respx

from app.llm.router import GEMINI_URL, MISTRAL_URL, AllProvidersFailedError, LLMRouter


def gemini_ok_payload(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def mistral_ok_payload(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


@pytest.fixture
def router() -> LLMRouter:
    return LLMRouter()


@respx.mock
@pytest.mark.asyncio
async def test_gemini_primary_success(router: LLMRouter):
    url = GEMINI_URL.format(model=router.settings.gemini_model)
    respx.post(url).mock(return_value=httpx.Response(200, json=gemini_ok_payload("pong")))

    result = await router.complete("ping")

    assert result.text == "pong"
    assert result.provider == "gemini"


@respx.mock
@pytest.mark.asyncio
async def test_fallback_to_mistral_when_gemini_fails(router: LLMRouter):
    gemini_url = GEMINI_URL.format(model=router.settings.gemini_model)
    respx.post(gemini_url).mock(return_value=httpx.Response(503, text="quota"))
    respx.post(MISTRAL_URL).mock(return_value=httpx.Response(200, json=mistral_ok_payload("pong mistral")))

    result = await router.complete("ping")

    assert result.text == "pong mistral"
    assert result.provider == "mistral"


@respx.mock
@pytest.mark.asyncio
async def test_all_providers_failed(router: LLMRouter):
    gemini_url = GEMINI_URL.format(model=router.settings.gemini_model)
    respx.post(gemini_url).mock(return_value=httpx.Response(500, text="down"))
    respx.post(MISTRAL_URL).mock(return_value=httpx.Response(500, text="down"))

    with pytest.raises(AllProvidersFailedError):
        await router.complete("ping")
