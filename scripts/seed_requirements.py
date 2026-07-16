"""Charge le referentiel d'exigences depuis data/requirements_v1.json vers Supabase.

Usage : python -m scripts.seed_requirements
Idempotent : upsert sur criterion_code.
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_supabase  # noqa: E402


def main() -> None:
    data_path = Path(__file__).resolve().parent.parent / "data" / "requirements_v1.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    version = payload["version"]
    rows = [
        {
            "article": r["article"],
            "criterion_code": r["criterion_code"],
            "criterion_text": r["criterion_text"],
            "category": r["category"],
            "version": version,
        }
        for r in payload["requirements"]
    ]

    supabase = get_supabase()
    result = supabase.table("requirements").upsert(rows, on_conflict="criterion_code").execute()
    print(f"Referentiel v{version} charge : {len(result.data)} criteres")


if __name__ == "__main__":
    main()
