"""Recherche vectorielle dans le corpus via la fonction SQL match_chunks."""

from dataclasses import dataclass

from app.db import get_supabase
from app.embeddings import embed_text


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    similarity: float


async def search(query: str, k: int = 8) -> list[RetrievedChunk]:
    """Embedde la requete et retourne les k chunks les plus proches."""
    query_embedding = await embed_text(query, task_type="RETRIEVAL_QUERY")
    supabase = get_supabase()
    result = supabase.rpc(
        "match_chunks",
        {"query_embedding": query_embedding, "match_count": k},
    ).execute()
    return [
        RetrievedChunk(
            chunk_id=row["id"],
            document_id=row["document_id"],
            content=row["content"],
            similarity=row["similarity"],
        )
        for row in result.data
    ]
