-- Add author and title to Sources table for Librarian metadata
ALTER TABLE "Sources"
ADD COLUMN IF NOT EXISTS author TEXT,
ADD COLUMN IF NOT EXISTS title TEXT;

-- Update Atoms to store original_author (for Citations)
ALTER TABLE "Atoms"
ADD COLUMN IF NOT EXISTS original_author TEXT;

-- Note: Atoms.type is TEXT, not ENUM (based on 002_add_atom_type.sql).
-- So we don't need to ALTER TYPE. We just use the string 'citation'.
