-- Migration 041: Add Categories table and link to Sources

-- 1. Create the Categories table
CREATE TABLE IF NOT EXISTS "public"."Categories" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user_id" UUID REFERENCES "auth"."users"(id) ON DELETE CASCADE NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMPTZ DEFAULT now() NOT NULL,
    "updated_at" TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Ensure category names are unique per user
CREATE UNIQUE INDEX IF NOT EXISTS "idx_unique_category_name_per_user" ON "public"."Categories" ("user_id", "name");

-- Enable Row Level Security for Categories
ALTER TABLE "public"."Categories" ENABLE ROW LEVEL SECURITY;

-- Policies for Categories
-- Allow authenticated users to view all categories they own
CREATE POLICY "Allow authenticated users to view their own categories"
ON "public"."Categories"
FOR SELECT
USING (auth.uid() = user_id);

-- Allow authenticated users to create categories
CREATE POLICY "Allow authenticated users to create categories"
ON "public"."Categories"
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Allow authenticated users to update their own categories
CREATE POLICY "Allow authenticated users to update their own categories"
ON "public"."Categories"
FOR UPDATE
USING (auth.uid() = user_id);

-- Allow authenticated users to delete their own categories
CREATE POLICY "Allow authenticated users to delete their own categories"
ON "public"."Categories"
FOR DELETE
USING (auth.uid() = user_id);

-- 2. Add category_id to Sources table
ALTER TABLE "public"."Sources"
ADD COLUMN "category_id" UUID REFERENCES "public"."Categories"(id) ON DELETE SET NULL;

-- 3. Remove series_id from Sources table
-- First, drop the foreign key constraint if it exists
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'Sources_series_id_fkey') THEN
        ALTER TABLE "public"."Sources" DROP CONSTRAINT "Sources_series_id_fkey";
    END IF;
END $$;

ALTER TABLE "public"."Sources"
DROP COLUMN IF EXISTS "series_id";

-- 4. Drop the Series table
DROP TABLE IF EXISTS "public"."Series";

-- 5. Update RLS policies on Sources to allow update of category_id
-- (No change needed, existing policy "Allow users to update their own source statuses" already covers this if it's general enough)
-- If a specific policy for series_id existed, it would need to be updated or removed.
-- The policy "Allow users to update their own source statuses" is broad and will cover category_id as well.

-- Optional: Create an index on category_id for faster lookups when grouping sources by category
CREATE INDEX IF NOT EXISTS "idx_sources_category_id" ON "public"."Sources" ("category_id");
