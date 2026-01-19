-- Migration 066: Update match_atoms RPC to be Epoch-Aware
-- This updates the core atom matching function to respect the "Shadow Canon" logic,
-- ensuring that atoms with a future discovery_epoch_id are not returned
-- unless the universe has progressed to that epoch.

CREATE OR REPLACE FUNCTION match_atoms(
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  query_user_id uuid,
  query_project_id uuid DEFAULT NULL,
  filter_lenses text[] DEFAULT NULL,
  filter_universe_ids uuid[] DEFAULT NULL,
  filter_storyline_id uuid DEFAULT NULL,
  query_epoch_id int DEFAULT NULL, -- Explicit Epoch Query
  filter_permanence_types text[] DEFAULT NULL,
  filter_start_date timestamptz DEFAULT NULL,
  filter_end_date timestamptz DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  name text,
  type text,
  content text,
  created_at timestamptz,
  user_id uuid,
  project_id uuid,
  universe_id uuid,
  storyline_id uuid,
  permanence text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id, a.name, a.type, a.content, a.created_at, a.user_id, a.project_id, a.universe_id, a.storyline_id, a.permanence::text,
    1 - (a.embedding <=> query_embedding) AS similarity
  FROM "Atoms" a
  WHERE (a.user_id = query_user_id OR a.project_id = query_project_id)
    AND 1 - (a.embedding <=> query_embedding) > match_threshold
    
    -- Explicit Epoch Protocol Filter
    AND (
      query_epoch_id IS NULL -- If no epoch is specified, return all (or handle as error).
      OR a.discovery_epoch_id IS NULL -- Always include atoms not gated by an epoch.
      OR a.discovery_epoch_id <= query_epoch_id -- Atom's discovery must be in the past or present.
    )

    -- Universe Firewall
    AND (filter_universe_ids IS NULL OR a.universe_id = ANY(filter_universe_ids))
    
    -- Storyline Continuity Logic
    AND (
      a.permanence IN ('static', 'archetypal')
      OR (a.storyline_id = filter_storyline_id AND a.permanence = 'dynamic')
    )
    
    -- Additional Filters
    AND (filter_permanence_types IS NULL OR a.permanence::text = ANY(filter_permanence_types))
    AND (filter_lenses IS NULL OR (a.metadata->>'cluster_name' = ANY(filter_lenses)))
    
    -- Temporal Filter
    AND (filter_start_date IS NULL OR a.created_at_source >= filter_start_date)
    AND (filter_end_date IS NULL OR a.created_at_source <= filter_end_date)
  
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
