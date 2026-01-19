-- Add resolution_source_id to Atoms to link questions to the source that answered them
ALTER TABLE "Atoms"
ADD COLUMN IF NOT EXISTS resolution_source_id UUID REFERENCES "Sources"(id);
