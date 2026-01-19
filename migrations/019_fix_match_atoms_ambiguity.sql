-- Fix ambiguous column reference in match_atoms
-- Explicitly alias metadata to the Atoms table

-- Drop the function first to allow signature/return type updates safely
DROP FUNCTION IF EXISTS match_atoms(vector, float, int, text[], timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION match_atoms(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_lenses text[],
  filter_start_date timestamp with time zone DEFAULT NULL,
  filter_end_date timestamp with time zone DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  user_id uuid,
  name text,
  type text,
  content text,
  embedding vector(1536),
  metadata jsonb,
  created_at timestamp with time zone,
  created_at_source timestamp with time zone,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    "Atoms".id,
    "Atoms".user_id,
    "Atoms".name,
    "Atoms".type,
    "Atoms".content,
    "Atoms".embedding,
    "Atoms".metadata,
    "Atoms".created_at,
    "Atoms".created_at_source,
    1 - ("Atoms".embedding <=> query_embedding) AS similarity
  FROM "Atoms"
  WHERE 1 - ("Atoms".embedding <=> query_embedding) > match_threshold
  -- Temporal Filter (The Time Machine)
  AND (
    filter_start_date IS NULL 
    OR "Atoms".created_at_source >= filter_start_date
  )
  AND (
    filter_end_date IS NULL 
    OR "Atoms".created_at_source <= filter_end_date
  )
  -- Lens Filter (Spectral Filtering)
  AND (
    filter_lenses IS NULL 
    OR cardinality(filter_lenses) = 0
    OR ("Atoms".metadata->>'cluster_name') = ANY(filter_lenses)
  )
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;