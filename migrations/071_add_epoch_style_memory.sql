-- Migration 071: Add Epoch Style and Memory
-- Adds columns to store the Prose Style Vector and Linear Memory Summarization for Epochs.

ALTER TABLE "Epochs"
ADD COLUMN "style_embedding" vector(768), -- Vertex AI Gecko/text-embedding-004 is 768 usually, but let's check. OpenAI is 1536.
ADD COLUMN "style_summary" TEXT,
ADD COLUMN "summary" TEXT;

COMMENT ON COLUMN "Epochs"."style_embedding" IS 'Vector representation of the prose style/tone of this Epoch.';
COMMENT ON COLUMN "Epochs"."style_summary" IS 'Text description of the prose style (e.g., "Dark, Gritty, Industrial").';
COMMENT ON COLUMN "Epochs"."summary" IS 'Linear Memory Summarization: A cohesive narrative summary of the entire Epoch.';
