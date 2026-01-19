-- Create a generic function to search for atoms (semantic memory + concepts)
-- Includes User ID filtering for security
create or replace function match_atoms (
  query_embedding vector(768), -- Adjusted to 768 for Gemini text-embedding-004
  match_threshold float,
  match_count int,
  p_user_id text
)
returns table (
  id uuid,
  name text,
  type text,
  metadata jsonb,
  embedding vector(768), -- Adjusted to 768
  created_at timestamptz,
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
    "Atoms".embedding,
    "Atoms".created_at,
    1 - ("Atoms".embedding <=> query_embedding) as similarity
  from "Atoms"
  where "Atoms".user_id = p_user_id
  and 1 - ("Atoms".embedding <=> query_embedding) > match_threshold
  order by "Atoms".embedding <=> query_embedding
  limit match_count;
end;
$$;