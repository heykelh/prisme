"""Ingere un fichier texte dans le corpus PRISME.

Usage (nouveau document) :
  python -m scripts.ingest_document --file corpus\\ai_act_fr.txt
    --title "AI Act (UE) 2024/1689" --doc-type regulation
    --url "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32024R1689"

Reprise d'une ingestion interrompue :
  ajouter --resume <document_id>
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.ingest import ingest_document  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion d'un document dans le corpus PRISME")
    parser.add_argument("--file", required=True, help="Chemin du fichier texte (UTF-8)")
    parser.add_argument("--title", required=True, help="Titre du document")
    parser.add_argument(
        "--doc-type",
        required=True,
        choices=["regulation", "guideline", "audit_ll144", "system_card", "registry_entry"],
    )
    parser.add_argument("--url", default=None, help="URL source du document")
    parser.add_argument("--resume", default=None, help="Id d'un document existant a reprendre")
    args = parser.parse_args()

    raw_text = Path(args.file).read_text(encoding="utf-8")
    document_id = asyncio.run(
        ingest_document(
            title=args.title,
            doc_type=args.doc_type,
            raw_text=raw_text,
            source_url=args.url,
            resume_document_id=args.resume,
        )
    )
    print(f"Document ingere : {document_id}")


if __name__ == "__main__":
    main()
