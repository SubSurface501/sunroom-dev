-- Migration 070: Add Narrative Ledger to Epochs
-- This column stores the chronological history of major narrative events
-- that occurred during this Epoch, allowing for psychological evolution.

ALTER TABLE "Epochs" 
ADD COLUMN narrative_ledger JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN "Epochs".narrative_ledger IS 'A chronological list of major events/turning points that occurred in this Epoch.';
