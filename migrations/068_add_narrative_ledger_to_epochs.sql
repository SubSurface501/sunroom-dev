ALTER TABLE "public"."Epochs"
ADD COLUMN "narrative_ledger" JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN "public"."Epochs"."narrative_ledger" IS 'Stores a mutable JSON object representing the current state vector of the narrative simulation (e.g., inventory, location, flags).';