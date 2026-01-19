ALTER TABLE "Storylines" ADD COLUMN IF NOT EXISTS "ledger" JSONB DEFAULT '{}'::jsonb;
