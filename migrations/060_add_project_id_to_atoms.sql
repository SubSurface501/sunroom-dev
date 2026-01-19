-- Add the project_id column to the Atoms table to support V7 Collective features
ALTER TABLE "Atoms"
ADD COLUMN project_id uuid;

-- Add RLS policies for the new column if necessary
-- For now, we rely on the function's query filters to handle access control.

-- We also need to update the match_atoms function again to correctly handle NULL project_id
-- This version ensures the join/filter logic works even if project_id is not set.

CREATE OR REPLACE FUNCTION match_atoms (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  query_user_id uuid,
  query_project_id uuid DEFAULT NULL,
  filter_lenses text[] DEFAULT NULL,
  filter_universe_ids uuid[] DEFAULT NULL,
  filter_permanence_types permanence_type[] DEFAULT NULL,
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
  permanence permanence_type,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    atoms.id,
    atoms.name,
    atoms.type,
    atoms.content,
    atoms.created_at,
    atoms.user_id,
    atoms.project_id,
    atoms.universe_id,
    atoms.storyline_id,
    atoms.permanence,
    1 - (atoms.embedding <=> query_embedding) AS similarity
  FROM "Atoms" AS atoms
  WHERE 
    -- Match user's own atoms OR atoms from the specified project
    (atoms.user_id = query_user_id OR (query_project_id IS NOT NULL AND atoms.project_id = query_project_id))
    AND 1 - (atoms.embedding <=> query_embedding) > match_threshold
    AND (filter_lenses IS NULL OR (atoms.metadata->>'cluster_name' = ANY(filter_lenses)))
    AND (filter_universe_ids IS NULL OR atoms.universe_id = ANY(filter_universe_ids))
    AND (filter_permanence_types IS NULL OR atoms.permanence = ANY(filter_permanence_types))
    AND (filter_start_date IS NULL OR atoms.created_at >= filter_start_date)
    AND (filter_end_date IS NULL OR atoms.created_at <= filter_end_date)
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
