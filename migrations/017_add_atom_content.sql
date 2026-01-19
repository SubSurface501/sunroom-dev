-- Add content column to Atoms table
ALTER TABLE "Atoms"
ADD COLUMN IF NOT EXISTS content TEXT;
