-- Migration 069: Add is_epic column to StoryVolumes

ALTER TABLE "StoryVolumes"
ADD COLUMN IF NOT EXISTS "is_epic" BOOLEAN DEFAULT FALSE;
