-- Migration 065: Add Epoch Protocol for Ontological Evolution
-- This migration introduces the concept of "Epochs" to allow universes
-- to undergo fundamental changes to their rules and canon over time.

-- 1. Create the epochs table
CREATE TABLE "Epochs" (
    id BIGSERIAL PRIMARY KEY,
    universe_id UUID NOT NULL REFERENCES "Universes"(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    archetype TEXT,
    system_anchor TEXT,
    prohibitions TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE "Epochs" ENABLE ROW LEVEL SECURITY;

-- Policies for epochs table
CREATE POLICY "Users can view epochs for their own universes"
    ON "Epochs" FOR SELECT
    USING (
        universe_id IN (SELECT id FROM "Universes" WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can insert epochs for universes they own"
    ON "Epochs" FOR INSERT
    WITH CHECK (
        universe_id IN (SELECT id FROM "Universes" WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can update epochs for universes they own"
    ON "Epochs" FOR UPDATE
    USING (
        universe_id IN (SELECT id FROM "Universes" WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can delete epochs for universes they own"
    ON "Epochs" FOR DELETE
    USING (
        universe_id IN (SELECT id FROM "Universes" WHERE user_id = auth.uid())
    );


-- 2. Add a foreign key for the active epoch to the universes table
ALTER TABLE "Universes"
ADD COLUMN active_epoch_id BIGINT REFERENCES "Epochs"(id) ON DELETE SET NULL;


-- 3. Add the epoch validity column to the atoms table for "Shadow Canon"
ALTER TABLE "Atoms"
ADD COLUMN discovery_epoch_id BIGINT REFERENCES "Epochs"(id) ON DELETE SET NULL;

-- Index for faster lookups
CREATE INDEX idx_atoms_discovery_epoch_id ON "Atoms"(discovery_epoch_id);

COMMENT ON COLUMN "Atoms".discovery_epoch_id IS 'Epoch in which this atom becomes "discoverable" in context retrieval. If NULL, it is always available.';

-- Grant usage on the new sequence if any, for the service role
GRANT USAGE, SELECT ON SEQUENCE "Epochs_id_seq" TO service_role;
