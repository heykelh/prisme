"""Point d'entree FastAPI de PRISME."""

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.llm.router import AllProvidersFailedError
from app.llm.router import router as llm_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="PRISME",
    description="Plateforme d'audit de conformite AI Act pour systemes IA de recrutement",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    status: str
    env: str
    version: str


class LLMPingRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


class LLMPingResponse(BaseModel):
    text: str
    provider: str
    model: str
    latency_ms: int


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", env=settings.app_env, version=app.version)


@app.post("/llm/ping", response_model=LLMPingResponse)
async def llm_ping(body: LLMPingRequest) -> LLMPingResponse:
    """Endpoint de verification du router LLM. Sera retire quand le moteur d'audit existera."""
    try:
        result = await llm_router.complete(prompt=body.prompt, system="Reponds en une phrase.")
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return LLMPingResponse(
        text=result.text,
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
    )
