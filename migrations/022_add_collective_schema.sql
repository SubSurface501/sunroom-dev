-- 1. Create Projects Table (Structure first)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- 2. Create Project Members Table (Dependent on projects)
CREATE TABLE IF NOT EXISTS project_members (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'collaborator', -- 'architect', 'bard', 'scribe'
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id)
);

ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;

-- 3. Apply Policies (Now that all tables exist)

-- Projects Policies
DROP POLICY IF EXISTS "Users can view projects they are members of" ON projects;
CREATE POLICY "Users can view projects they are members of" ON projects
    FOR SELECT USING (
        auth.uid() = owner_id OR 
        EXISTS (SELECT 1 FROM project_members WHERE project_id = projects.id AND user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can create projects" ON projects;
CREATE POLICY "Users can create projects" ON projects
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

-- Project Members Policies
DROP POLICY IF EXISTS "Members can view project roster" ON project_members;
CREATE POLICY "Members can view project roster" ON project_members
    FOR SELECT USING (
        project_id IN (
            SELECT my_projects.project_id FROM project_members my_projects WHERE my_projects.user_id = auth.uid()
        )
    );

-- 4. Create Lens Grants Table
CREATE TABLE IF NOT EXISTS active_project_lenses (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    cluster_label TEXT, -- e.g., "Physics"
    mode TEXT, -- 'style' or 'context'
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id, cluster_label)
);

ALTER TABLE active_project_lenses ENABLE ROW LEVEL SECURITY;

-- 5. Secure Atoms Table (The Sovereignty Layer)
ALTER TABLE "Atoms" ENABLE ROW LEVEL SECURITY;

-- Add project_id to StoryVolumes to link stories to the collective
ALTER TABLE "StoryVolumes" 
ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id);

-- Drop existing policies to avoid conflicts if re-running
DROP POLICY IF EXISTS "Users can CRUD their own atoms" ON "Atoms";

CREATE POLICY "Users can CRUD their own atoms" ON "Atoms"
    USING (auth.uid() = user_id);

-- 6. Update match_atoms RPC to support The Collective
DROP FUNCTION IF EXISTS match_atoms(vector, float, int, text[], timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION match_atoms(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_lenses text[],
  filter_start_date timestamp with time zone DEFAULT NULL,
  filter_end_date timestamp with time zone DEFAULT NULL,
  query_user_id uuid DEFAULT NULL,   -- The user running the query
  query_project_id uuid DEFAULT NULL -- The project context (optional)
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
  -- Identity Layer:
  AND (
    -- 1. My Atoms (Default behavior if no project)
    (query_user_id IS NOT NULL AND "Atoms".user_id = query_user_id)
    OR
    -- 2. Project Atoms (The Collective)
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
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;