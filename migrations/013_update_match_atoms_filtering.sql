-- Update match_atoms to support filtering by cluster names
-- Drop old signatures to avoid ambiguity
drop function if exists match_atoms(vector(768), float, int);
drop function if exists match_atoms(vector(768), float, int, text[]);

create or replace function match_atoms (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  filter_clusters text[] default null
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
  and (
    filter_clusters is null 
    or 
    cardinality(filter_clusters) = 0
    or
    (metadata->>'cluster_name') = any(filter_clusters)
  )
  order by "Atoms".embedding <=> query_embedding
  limit match_count;
end;
$$;
