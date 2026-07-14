# PRISME

Plateforme d'audit de conformite AI Act pour les systemes IA de recrutement.

Les systemes IA de recrutement sont classes a haut risque par l'annexe III du reglement europeen sur l'IA. PRISME les audite contre les exigences des articles 9 a 15, sur la base de documents publics reels (audits de biais NYC Local Law 144, registres publics, system cards), avec des verdicts structures, sources et mesures.

## Principes

- **Verdicts encadres** : conforme / non conforme / non verifiable. Citation source obligatoire, sinon le verdict est non verifiable, jamais invente.
- **Corpus reel** : aucune donnee fictive. Tout le corpus est public, primaire et citable.
- **Auditabilite** : chaque run est journalise (versions du referentiel, provider LLM, verdicts, citations).
- **Multi-provider** : Gemini 2.5 Flash en primaire, Mistral en fallback.

## Stack

FastAPI (Python 3.12) | Supabase (Postgres + pgvector) | Gemini 2.5 Flash + Mistral | Next.js 15 | GitHub Actions | Render + Vercel

## Demarrage local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # puis remplir les cles
uvicorn app.main:app --reload
```

API sur http://127.0.0.1:8000, documentation interactive sur http://127.0.0.1:8000/docs

## Tests

```powershell
pytest -v
ruff check .
```

## Statut

Phase P0 : fondations. Referentiel d'exigences et pipeline RAG en cours (P1).

## Methodologie et limites

Les analyses portent exclusivement sur des documents publics. L'outil produit des evaluations indicatives, pas des certifications. Les verdicts LLM sont encadres par des citations obligatoires verifiees de facon deterministe et des mesures de stabilite publiees dans ce README a partir de la phase P2.