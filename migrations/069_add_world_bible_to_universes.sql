ALTER TABLE "public"."Universes"
ADD COLUMN "world_bible" JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN "public"."Universes"."world_bible" IS 'Stores an immutable JSON object of foundational, non-negotiable facts about the universe (e.g., character names, core laws, forbidden concepts).';