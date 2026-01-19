-- Function to match atoms by embedding similarity
-- Drops the function if it already exists to ensure a clean definition
-- We need to drop specifically with signature if it exists
drop function if exists match_atoms(vector(768), float, int);

create or replace function match_atoms (
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  name text,
  type text,
  metadata jsonb,
  content text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    "Atoms".id,
    "Atoms".name,
    "Atoms".type,
    "Atoms".metadata,
    "Atoms".content,
    1 - ("Atoms".embedding <=> query_embedding) as similarity
  from "Atoms"
  where 1 - ("Atoms".embedding <=> query_embedding) > match_threshold
  order by "Atoms".embedding <=> query_embedding
  limit match_count;
end;
$$;