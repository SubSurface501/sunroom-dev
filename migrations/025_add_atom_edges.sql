-- migrations/025_add_atom_edges.sql

DO $$
BEGIN
    -- Drop indexes if they exist
    DROP INDEX IF EXISTS idx_edges_source;
    DROP INDEX IF EXISTS idx_edges_target;

    -- Drop table if it exists (CASCADE will remove dependent objects like constraints)
    DROP TABLE IF EXISTS "AtomEdges" CASCADE;

    -- Recreate the table with correct schema
    CREATE TABLE IF NOT EXISTS "AtomEdges" (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        source_atom_id UUID NOT NULL REFERENCES "Atoms"(id) ON DELETE CASCADE,
        target_atom_id UUID NOT NULL REFERENCES "Atoms"(id) ON DELETE CASCADE,
        
        -- 'narrative_flow' (Sequence) or 'semantic_similarity' (Vector)
        relationship_type TEXT NOT NULL, 
        
        -- 1.0 for sequence, 0.0-1.0 for cosine similarity
        weight FLOAT DEFAULT 1.0, 
        
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- Prevent duplicate edges between the same two atoms
        CONSTRAINT unique_atom_edge_rel UNIQUE (source_atom_id, target_atom_id, relationship_type)
    );

    -- Recreate indices for fast Graph Traversal (BFS/DFS)
    CREATE INDEX IF NOT EXISTS idx_edges_source ON "AtomEdges"(source_atom_id);
    CREATE INDEX IF NOT EXISTS idx_edges_target ON "AtomEdges"(target_atom_id);
END
$$;
