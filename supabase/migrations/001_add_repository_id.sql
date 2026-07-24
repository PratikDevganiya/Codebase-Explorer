-- Preserve the repository IDs already used by API responses, vector metadata,
-- file browsing routes, and the React frontend.
alter table public.projects
add column if not exists repository_id text;

update public.projects
set repository_id = 'repo_' || substr(replace(id::text, '-', ''), 1, 16)
where repository_id is null;

alter table public.projects
alter column repository_id set not null;

create unique index if not exists projects_repository_id_idx
on public.projects(repository_id);
