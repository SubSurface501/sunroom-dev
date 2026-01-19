-- Add metadata and type columns to Atoms table if they don't exist
ALTER TABLE "Atoms" 
ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'concept',
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
