"""Embeddings via l'API Gemini (gemini-embedding-001, reduit a 768 dimensions).

text-embedding-004 a ete arrete par Google le 14 janvier 2026.
gemini-embedding-001 sort en 3072 dims par defaut ; on demande 768 pour
correspondre au schema Supabase vector(768), et on normalise le vecteur
(les sorties reduites ne sont pas normalisees par l'API).
La cle passe en header x-goog-api-key, jamais dans l'URL.
L'ingestion utilise l'endpoint batch : jusqu'a 100 textes par requete,
ce qui divise la consommation de quota par la taille du lot.
"""

import logging
import math

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger("prisme.embeddings")

EMBED_MODEL = "gemini-embedding-001"
EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent"
BATCH_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:batchEmbedContents"
EMBED_DIM = 768


class EmbeddingError(Exception):
    """Erreur retryable du service d'embedding."""


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _check_status(response: httpx.Response) -> None:
    if response.status_code in (429, 500, 502, 503, 504):
        raise EmbeddingError(f"HTTP {response.status_code}: {response.text[:200]}")
    response.raise_for_status()


@retry(
    retry=retry_if_exception_type(EmbeddingError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
async def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Retourne le vecteur d'embedding normalise d'un texte (768 dims).

    task_type : RETRIEVAL_DOCUMENT pour l'ingestion, RETRIEVAL_QUERY pour la recherche.
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            EMBED_URL,
            headers={"x-goog-api-key": settings.gemini_api_key},
            json={
                "model": f"models/{EMBED_MODEL}",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
                "outputDimensionality": EMBED_DIM,
            },
        )
    _check_status(response)
    data = response.json()
    try:
        values = data["embedding"]["values"]
    except KeyError as exc:
        raise EmbeddingError(f"Reponse embedding inattendue: {data}") from exc
    if len(values) != EMBED_DIM:
        raise EmbeddingError(f"Dimension inattendue: {len(values)} au lieu de {EMBED_DIM}")
    return _normalize(values)


@retry(
    retry=retry_if_exception_type(EmbeddingError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
async def embed_batch(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embedde un lot de textes en une seule requete API (max 100).

    Une requete batch consomme une seule unite de quota requetes,
    quel que soit le nombre de textes du lot.
    """
    if not texts:
        return []
    if len(texts) > 100:
        raise ValueError("Maximum 100 textes par lot")

    settings = get_settings()
    payload = {
        "requests": [
            {
                "model": f"models/{EMBED_MODEL}",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
                "outputDimensionality": EMBED_DIM,
            }
            for text in texts
        ]
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            BATCH_URL,
            headers={"x-goog-api-key": settings.gemini_api_key},
            json=payload,
        )
    _check_status(response)
    data = response.json()
    try:
        vectors = [item["values"] for item in data["embeddings"]]
    except KeyError as exc:
        raise EmbeddingError(f"Reponse batch inattendue: {data}") from exc
    if len(vectors) != len(texts):
        raise EmbeddingError(f"Lot incomplet: {len(vectors)} vecteurs pour {len(texts)} textes")
    for v in vectors:
        if len(v) != EMBED_DIM:
            raise EmbeddingError(f"Dimension inattendue: {len(v)} au lieu de {EMBED_DIM}")
    return [_normalize(v) for v in vectors]
