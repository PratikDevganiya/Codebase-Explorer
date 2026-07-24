alter table public.projects
add column if not exists storage_prefix text;

insert into storage.buckets (id, name, public, file_size_limit)
values ('project-sources', 'project-sources', false, 5242880)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit;
