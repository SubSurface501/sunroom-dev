-- Migration 072: Add epoch_id to StoryVolumes
ALTER TABLE "StoryVolumes"
ADD COLUMN IF NOT EXISTS "epoch_id" BIGINT REFERENCES "Epochs"(id) ON DELETE SET NULL;
