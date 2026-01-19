-- Create StoryVolumes table
CREATE TABLE IF NOT EXISTS "StoryVolumes" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title TEXT NOT NULL,
    root_concept TEXT NOT NULL,
    graph_structure JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'draft', -- draft, hydrated, text_ready, assets_ready, published
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Update Trailheads table to link to StoryVolumes
ALTER TABLE "Trailheads" 
ADD COLUMN IF NOT EXISTS volume_id UUID REFERENCES "StoryVolumes"(id),
ADD COLUMN IF NOT EXISTS parent_node_id UUID REFERENCES "Trailheads"(id),
ADD COLUMN IF NOT EXISTS research_status TEXT DEFAULT 'pending'; -- pending, complete
