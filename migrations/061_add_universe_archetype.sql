-- Add archetype column to Universes table
ALTER TABLE "Universes"
ADD COLUMN archetype TEXT;

-- Optional: Add a default value if needed, or handle it in application logic
-- UPDATE "Universes" SET archetype = 'UNDEFINED' WHERE archetype IS NULL;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_universes_archetype ON "Universes"(archetype);
