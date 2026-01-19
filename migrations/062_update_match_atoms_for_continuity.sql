-- Update match_atoms to support Storyline Continuity
-- This function ensures that when fetching context:
-- 1. 'static' and 'archetypal' atoms are always included (The "World Bible").
-- 2. 'dynamic' atoms are ONLY included if they belong to the current storyline (The "Plot Ledger").

DROP FUNCTION IF EXISTS match_atoms(vector, float, int, text[], timestamp with time zone, timestamp with time zone, uuid, uuid);

CREATE OR REPLACE FUNCTION match_atoms(
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  filter_lenses text[],
  filter_start_date timestamp with time zone DEFAULT NULL,
  filter_end_date timestamp with time zone DEFAULT NULL,
  query_user_id uuid DEFAULT NULL,
  query_project_id uuid DEFAULT NULL,
  p_storyline_id uuid DEFAULT NULL -- ADDED for storyline isolation
)
RETURNS TABLE (
  id uuid,
  user_id uuid,
  name text,
  type text,
  content text,
  embedding vector(768),
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
  -- Identity Layer:
  AND (
    (query_user_id IS NOT NULL AND "Atoms".user_id = query_user_id)
    OR
    (query_project_id IS NOT NULL AND "Atoms".user_id IN (
        SELECT pm.user_id 
        FROM project_members pm 
        WHERE pm.project_id = query_project_id
    ))
  )
  -- Temporal Filter
  AND (
    filter_start_date IS NULL 
    OR "Atoms".created_at_source >= filter_start_date
  )
  AND (
    filter_end_date IS NULL 
    OR "Atoms".created_at_source <= filter_end_date
  )
  -- Lens Filter
  AND (
    filter_lenses IS NULL 
    OR cardinality(filter_lenses) = 0
    OR ("Atoms".metadata->>'cluster_name') = ANY(filter_lenses)
  )
  -- *** NEW: Continuity / Storyline Isolation Filter ***
  AND (
    "Atoms".permanence IN ('static', 'archetypal')
    OR
    (
      "Atoms".permanence = 'dynamic' AND
      "Atoms".storyline_id = p_storyline_id
    )
  )
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
