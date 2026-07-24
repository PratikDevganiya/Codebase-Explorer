create table if not exists public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    repository_id text not null
        references public.projects(repository_id)
        on delete cascade,
    session_id uuid not null,
    role text not null check (role in ('user', 'assistant')),
    content text not null check (length(trim(content)) > 0),
    sources jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists chat_messages_session_project_idx
on public.chat_messages(session_id, repository_id, created_at);

alter table public.chat_messages enable row level security;
