-- Add columns to track the status and estimated time for long-running ingestion jobs (e.g., audio transcription).

ALTER TABLE "public"."Sources"
ADD COLUMN "processing_status" TEXT DEFAULT 'completed' NOT NULL,
ADD COLUMN "estimated_processing_time_minutes" INTEGER DEFAULT 0 NOT NULL;

-- Add a policy to allow users to update the status of their own sources.
-- This is necessary for the Celery worker to update the status as it processes the file.
CREATE POLICY "Allow users to update their own source statuses"
ON "public"."Sources"
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Since RLS is enabled, we need to ensure the service_role can still bypass it.
-- The default policies usually handle this, but it's good practice to be explicit if issues arise.
-- No new policy needed for service_role as it bypasses RLS by default.

-- It might be useful to have an index on the status for faster lookups of processing jobs.
CREATE INDEX "ix_sources_processing_status" ON "public"."Sources" ("processing_status");
