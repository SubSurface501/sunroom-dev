ALTER TABLE "StoryVolumes"
ADD COLUMN universe_id uuid REFERENCES "Universes"(id) ON DELETE SET NULL,
ADD COLUMN storyline_id uuid REFERENCES "Storylines"(id) ON DELETE SET NULL;

-- Optional: Add RLS for StoryVolumes to filter by universe and storyline if needed
-- This assumes the existing RLS on StoryVolumes already covers user ownership.
-- If not, a policy would need to be added/modified here.
