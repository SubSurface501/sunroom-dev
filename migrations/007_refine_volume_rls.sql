-- Refine RLS for StoryVolumes to support authenticated owner access and public read for published volumes

-- Drop existing public read policy for anon role (if any)
DROP POLICY IF EXISTS "Public Read Volumes" ON "StoryVolumes";

-- Policy 1: Authenticated users can manage their own volumes
-- Grants SELECT, INSERT, UPDATE, DELETE access to authenticated users for volumes where user_id matches their auth.uid()
CREATE POLICY "User Owns Volumes" ON "StoryVolumes"
FOR ALL TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy 2: Anonymous users can read published volumes
-- Grants SELECT access to anonymous users for volumes with status 'published'
CREATE POLICY "Public Read Published Volumes" ON "StoryVolumes"
FOR SELECT TO anon
USING (status = 'published');

-- Note: The 'Service Role Full Access Volumes' policy (if it exists) should remain separate and untouched
-- as it provides backend full access regardless of user_id for server-side operations.
