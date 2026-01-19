-- 1. Create the Source Type Enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE source_type_enum AS ENUM (
        'youtube_transcript',
        'personal_journal',
        'uploaded_text',
        'web_scrape',
        'youtube_video' -- Legacy support if needed
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Upgrade Sources Table
-- Add columns if they don't exist
ALTER TABLE "Sources"
ADD COLUMN IF NOT EXISTS source_type source_type_enum DEFAULT 'uploaded_text',
ADD COLUMN IF NOT EXISTS original_publication_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS date_confidence FLOAT DEFAULT 1.0 CHECK (date_confidence >= 0.0 AND date_confidence <= 1.0);

-- 3. Upgrade Atoms Table
-- created_at_source already added in 014, but let's double check/ensure index
-- Note: We can't easily ADD COLUMN IF NOT EXISTS with TYPE change in one go if it exists differently.
-- Assuming 014 added it correctly. We will just ensure the index.

CREATE INDEX IF NOT EXISTS idx_atoms_created_at_source ON "Atoms"(created_at_source);

-- Add date_confidence to Atoms as well, to support atomic-level uncertainty
ALTER TABLE "Atoms"
ADD COLUMN IF NOT EXISTS date_confidence FLOAT DEFAULT 1.0 CHECK (date_confidence >= 0.0 AND date_confidence <= 1.0);
