create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    title text not null default 'New chat'
        check (length(trim(title)) between 1 and 120),
    legacy_session_id uuid,
    legacy_repository_id text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.conversation_projects (
    conversation_id uuid not null
        references public.conversations(id)
        on delete cascade,
    repository_id text not null
        references public.projects(repository_id)
        on delete cascade,
    position integer not null default 0,
    primary key (conversation_id, repository_id)
);

alter table public.chat_messages
add column if not exists conversation_id uuid
    references public.conversations(id)
    on delete cascade;

create index if not exists conversations_updated_at_idx
on public.conversations(updated_at desc);

create unique index if not exists conversations_legacy_scope_idx
on public.conversations(legacy_session_id, legacy_repository_id)
where legacy_session_id is not null and legacy_repository_id is not null;

create index if not exists conversation_projects_repository_idx
on public.conversation_projects(repository_id, conversation_id);

create index if not exists chat_messages_conversation_idx
on public.chat_messages(conversation_id, created_at);

alter table public.conversations enable row level security;
alter table public.conversation_projects enable row level security;

-- Preserve chat history created before named conversations were introduced.
insert into public.conversations (
    title,
    legacy_session_id,
    legacy_repository_id,
    created_at,
    updated_at
)
select
    left(
        coalesce(
            (
                array_agg(content order by created_at)
                filter (where role = 'user')
            )[1],
            'Previous chat'
        ),
        120
    ),
    session_id,
    repository_id,
    min(created_at),
    max(created_at)
from public.chat_messages
where conversation_id is null
group by session_id, repository_id
on conflict (legacy_session_id, legacy_repository_id)
where legacy_session_id is not null and legacy_repository_id is not null
do nothing;

insert into public.conversation_projects (
    conversation_id,
    repository_id,
    position
)
select id, legacy_repository_id, 0
from public.conversations
where legacy_repository_id is not null
on conflict do nothing;

update public.chat_messages as message
set conversation_id = conversation.id
from public.conversations as conversation
where message.conversation_id is null
  and conversation.legacy_session_id = message.session_id
  and conversation.legacy_repository_id = message.repository_id;
