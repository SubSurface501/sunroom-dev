-- Add media_url and visual_description to Atoms for multi-modal support
ALTER TABLE "Atoms"
ADD COLUMN IF NOT EXISTS media_url TEXT,
ADD COLUMN IF NOT EXISTS visual_description TEXT;
