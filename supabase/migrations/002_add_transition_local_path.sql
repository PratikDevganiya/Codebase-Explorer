-- Temporary compatibility field used while project files still live on the
-- API host. A later storage migration will replace this with a storage prefix.
alter table public.projects
add column if not exists local_path text;
