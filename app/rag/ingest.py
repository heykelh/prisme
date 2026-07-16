"""Ingestion d'un document dans le corpus : insertion, chunking, embeddings batch, stockage.

Reprise sur incident : si un document existe deja, l'ingestion repart du premier
chunk manquant (le chunking etant deterministe, les index sont stables).
"""

import asyncio
import logging

from app.db import get_supabase
from app.embeddings import embed_batch
from app.rag.chunking import chunk_text

logger = logging.getLogger("prisme.ingest")

VALID_DOC_TYPES = {"regulation", "guideline", "audit_ll144", "system_card", "registry_entry"}
BATCH_SIZE = 20


async def ingest_document(
    title: str,
    doc_type: str,
    raw_text: str,
    source_url: str | None = None,
    resume_document_id: str | None = None,
) -> str:
    """Ingere un document complet par lots. Retourne l'id du document.

    resume_document_id : reprend l'ingestion d'un document existant
    a partir du premier chunk manquant.
    """
    if doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"doc_type invalide: {doc_type}. Valides: {sorted(VALID_DOC_TYPES)}")

    supabase = get_supabase()

    if resume_document_id:
        document_id = resume_document_id
        existing = (
            supabase.table("chunks")
            .select("chunk_index")
            .eq("document_id", document_id)
            .order("chunk_index", desc=True)
            .limit(1)
            .execute()
        )
        start_index = existing.data[0]["chunk_index"] + 1 if existing.data else 0
        logger.info("reprise du document %s a partir du chunk %d", document_id, start_index)
    else:
        doc_result = (
            supabase.table("documents")
            .insert({"title": title, "doc_type": doc_type, "raw_text": raw_text, "source_url": source_url})
            .execute()
        )
        document_id = doc_result.data[0]["id"]
        start_index = 0
        logger.info("document cree id=%s title=%s", document_id, title)

    chunks = chunk_text(raw_text)
    total = len(chunks)
    logger.info("decoupage: %d chunks, ingestion a partir de l'index %d", total, start_index)

    for batch_start in range(start_index, total, BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]
        embeddings = await embed_batch(batch, task_type="RETRIEVAL_DOCUMENT")
        rows = [
            {
                "document_id": document_id,
                "chunk_index": batch_start + offset,
                "content": content,
                "embedding": embedding,
            }
            for offset, (content, embedding) in enumerate(zip(batch, embeddings))
        ]
        supabase.table("chunks").insert(rows).execute()
        logger.info("progression: %d/%d chunks", min(batch_start + BATCH_SIZE, total), total)
        await asyncio.sleep(8.0)  # lissage du debit sur le free tier

    logger.info("ingestion terminee: %d chunks pour document %s", total, document_id)
    return document_id
