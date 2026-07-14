-- PRISME : schema P0
-- Referentiel d'exigences + corpus vectorise + runs d'audit

create extension if not exists vector;

-- Referentiel : chaque article de l'AI Act decompose en criteres atomiques verifiables
create table if not exists requirements (
    id uuid primary key default gen_random_uuid(),
    article text not null,                 -- ex: 'Article 10'
    criterion_code text not null unique,   -- ex: 'ART10-C03'
    criterion_text text not null,          -- le critere verifiable, formulation atomique
    category text not null,                -- risk_management | data_governance | documentation | logging | transparency | human_oversight | robustness
    version int not null default 1,
    created_at timestamptz not null default now()
);

-- Documents du corpus (reglementaire) et documents audites
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    doc_type text not null,                -- regulation | guideline | audit_ll144 | system_card | registry_entry
    source_url text,
    raw_text text not null,
    created_at timestamptz not null default now()
);

-- Chunks vectorises pour le RAG (dimension 768, embeddings Gemini text-embedding-004)
create table if not exists chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    chunk_index int not null,
    content text not null,
    embedding vector(768),
    created_at timestamptz not null default now()
);

create index if not exists chunks_embedding_idx
    on chunks using hnsw (embedding vector_cosine_ops);

-- Runs d'audit : journalisation complete, un outil d'audit doit etre auditable
create table if not exists audit_runs (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id),
    requirements_version int not null,
    llm_provider text,
    status text not null default 'running', -- running | completed | failed
    started_at timestamptz not null default now(),
    completed_at timestamptz
);

-- Verdicts : un par exigence et par run, avec citation obligatoire
create table if not exists verdicts (
    id uuid primary key default gen_random_uuid(),
    audit_run_id uuid not null references audit_runs(id) on delete cascade,
    requirement_id uuid not null references requirements(id),
    verdict text not null check (verdict in ('conforme', 'non_conforme', 'non_verifiable')),
    justification text not null,
    citation text,                          -- extrait verbatim du document audite, null uniquement si non_verifiable
    citation_verified boolean not null default false,  -- verification deterministe par sous-chaine
    created_at timestamptz not null default now()
);

-- Recherche vectorielle
create or replace function match_chunks(
    query_embedding vector(768),
    match_count int default 8
)
returns table (id uuid, document_id uuid, content text, similarity float)
language sql stable as $$
    select c.id, c.document_id, c.content,
           1 - (c.embedding <=> query_embedding) as similarity
    from chunks c
    where c.embedding is not null
    order by c.embedding <=> query_embedding
    limit match_count;
$$;