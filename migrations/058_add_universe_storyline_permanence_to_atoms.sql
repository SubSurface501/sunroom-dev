-- First, create the ENUM type for permanence
CREATE TYPE permanence_type AS ENUM ('static', 'dynamic', 'archetypal');

ALTER TABLE "Atoms"
ADD COLUMN universe_id uuid REFERENCES "Universes"(id) ON DELETE SET NULL,
ADD COLUMN storyline_id uuid REFERENCES "Storylines"(id) ON DELETE SET NULL,
ADD COLUMN permanence permanence_type NOT NULL DEFAULT 'dynamic', -- Default to dynamic
ADD COLUMN source_volume_id uuid REFERENCES "StoryVolumes"(id) ON DELETE SET NULL;

-- Optional: Add RLS policies for Atoms if needed, considering the new columns.
-- Existing RLS might need adjustment.
