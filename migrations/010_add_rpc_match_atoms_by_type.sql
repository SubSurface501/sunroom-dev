-- Create a function to search for atoms by type
create or replace function match_atoms_by_type (
  query_embedding vector(768),
  atom_type text,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  name text,
  type text,
  metadata jsonb,
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
    1 - ("Atoms".embedding <=> query_embedding) as similarity
  from "Atoms"
  where "Atoms".type = match_atoms_by_type.atom_type
  and 1 - ("Atoms".embedding <=> query_embedding) > match_threshold
  order by "Atoms".embedding <=> query_embedding
  limit match_count;
end;
$$;
