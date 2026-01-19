-- Add temporal columns to Atoms table
-- 'created_at_source' is the original creation date of the content (e.g. YouTube publish date)
-- 'epoch_label' is a semantic tag for the time period (e.g. "2023_q1_growth")

ALTER TABLE "Atoms"
ADD COLUMN IF NOT EXISTS created_at_source TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS epoch_label TEXT;

-- Index for faster range queries
CREATE INDEX IF NOT EXISTS atoms_created_at_source_idx ON "Atoms" (created_at_source);
