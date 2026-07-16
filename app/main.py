"""Point d'entree FastAPI de PRISME."""

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import get_supabase
from app.llm.router import AllProvidersFailedError
from app.llm.router import router as llm_router
from app.rag.retrieve import search

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="PRISME",
    description="Plateforme d'audit de conformite AI Act pour systemes IA de recrutement",
    version="0.2.0",
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


class RequirementOut(BaseModel):
    article: str
    criterion_code: str
    criterion_text: str
    category: str
    version: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    k: int = Field(default=8, ge=1, le=20)


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    similarity: float


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


@app.get("/requirements", response_model=list[RequirementOut])
async def list_requirements() -> list[RequirementOut]:
    """Le referentiel d'exigences actif, trie par code."""
    supabase = get_supabase()
    result = supabase.table("requirements").select("*").order("criterion_code").execute()
    return [RequirementOut(**row) for row in result.data]


@app.post("/rag/search", response_model=list[SearchResult])
async def rag_search(body: SearchRequest) -> list[SearchResult]:
    """Recherche vectorielle dans le corpus reglementaire."""
    results = await search(body.query, body.k)
    return [
        SearchResult(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            content=r.content,
            similarity=r.similarity,
        )
        for r in results
    ]
