"""Router LLM multi-provider de PRISME.

Strategie : Gemini 2.5 Flash en primaire (contexte long, free tier genereux),
Mistral en fallback (LLM europeen, argument narratif conformite).
Chaque appel est trace avec le provider utilise et la latence, car un outil
d'audit doit etre lui-meme auditable.
Les cles API passent en header, jamais dans l'URL, pour ne pas fuiter dans
les logs et tracebacks.
"""

import logging
import time
from dataclasses import dataclass

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

logger = logging.getLogger("prisme.llm")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


class ProviderError(Exception):
    """Erreur retryable d'un provider LLM (reseau, 5xx, quota)."""


class AllProvidersFailedError(Exception):
    """Tous les providers ont echoue. L'appelant doit degrader proprement."""


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_ms: int


def _raise_for_retryable(response: httpx.Response) -> None:
    if response.status_code in (429, 500, 502, 503, 504):
        raise ProviderError(f"HTTP {response.status_code}: {response.text[:200]}")
    response.raise_for_status()


class LLMRouter:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(self, prompt: str, system: str = "", temperature: float = 0.0) -> LLMResponse:
        """Tente Gemini, bascule sur Mistral si echec. Temperature 0 par defaut :
        un auditeur ne fait pas preuve de creativite."""
        try:
            return await self._call_gemini(prompt, system, temperature)
        except (ProviderError, httpx.HTTPError) as exc:
            logger.warning("Gemini indisponible, bascule sur Mistral: %s", exc)
        try:
            return await self._call_mistral(prompt, system, temperature)
        except (ProviderError, httpx.HTTPError) as exc:
            logger.error("Mistral indisponible egalement: %s", exc)
            raise AllProvidersFailedError("Aucun provider LLM disponible") from exc

    @retry(
        retry=retry_if_exception_type(ProviderError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _call_gemini(self, prompt: str, system: str, temperature: float) -> LLMResponse:
        settings = self.settings
        url = GEMINI_URL.format(model=settings.gemini_model)
        payload: dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=payload,
            )
        _raise_for_retryable(response)
        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Reponse Gemini inattendue: {data}") from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("gemini ok model=%s latency_ms=%d", settings.gemini_model, latency_ms)
        return LLMResponse(text=text, provider="gemini", model=settings.gemini_model, latency_ms=latency_ms)

    @retry(
        retry=retry_if_exception_type(ProviderError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _call_mistral(self, prompt: str, system: str, temperature: float) -> LLMResponse:
        settings = self.settings
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                MISTRAL_URL,
                headers={"Authorization": f"Bearer {settings.mistral_api_key}"},
                json={
                    "model": settings.mistral_model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
        _raise_for_retryable(response)
        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Reponse Mistral inattendue: {data}") from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("mistral ok model=%s latency_ms=%d", settings.mistral_model, latency_ms)
        return LLMResponse(text=text, provider="mistral", model=settings.mistral_model, latency_ms=latency_ms)


router = LLMRouter()
