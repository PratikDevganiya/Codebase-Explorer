create extension if not exists vector;

create table if not exists public.code_chunks (
    id text primary key,
    repository_id text not null
        references public.projects(repository_id)
        on delete cascade,
    embedding vector(384) not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists code_chunks_repository_id_idx
on public.code_chunks(repository_id);

create index if not exists code_chunks_embedding_hnsw_idx
on public.code_chunks
using hnsw (embedding vector_cosine_ops);

alter table public.code_chunks enable row level security;

create or replace function public.match_code_chunks(
    query_embedding vector(384),
    match_count integer default 20,
    metadata_filter jsonb default '{}'::jsonb
)
returns table (
    id text,
    repository_id text,
    metadata jsonb,
    distance double precision
)
language sql
stable
set search_path = public
as $$
    select
        code_chunks.id,
        code_chunks.repository_id,
        code_chunks.metadata,
        (code_chunks.embedding <=> query_embedding)::double precision
            as distance
    from public.code_chunks
    where code_chunks.metadata @> metadata_filter
    order by code_chunks.embedding <=> query_embedding
    limit greatest(match_count, 0);
$$;
