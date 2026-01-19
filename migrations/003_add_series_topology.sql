-- Create Series table to group sequential videos
CREATE TABLE IF NOT EXISTS "Series" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add topology columns to Sources
ALTER TABLE "Sources" 
ADD COLUMN IF NOT EXISTS series_id UUID REFERENCES "Series"(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS series_index INTEGER, -- Order in the playlist (1, 2, 3...)
ADD COLUMN IF NOT EXISTS knowledge_state_snapshot JSONB; -- The "State of Knowledge" after this video

-- Add a specific type for Frontier Nodes if strictly necessary, 
-- though we can just use the existing 'type' column with a new value 'frontier'.
-- We might want a separate table for "FrontierNodes" if they are distinct from Atoms,
-- but for now, treating them as Atoms with a specific type is cleaner for the MVP.
