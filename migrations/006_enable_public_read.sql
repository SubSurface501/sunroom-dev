-- Enable RLS and allow public read access for the Story Player

-- StoryVolumes
ALTER TABLE "StoryVolumes" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public Read Volumes" ON "StoryVolumes";
CREATE POLICY "Public Read Volumes" ON "StoryVolumes" FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Volumes" ON "StoryVolumes";
CREATE POLICY "Service Role Full Access Volumes" ON "StoryVolumes" FOR ALL TO service_role USING (true);


-- Trailheads
ALTER TABLE "Trailheads" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public Read Trailheads" ON "Trailheads";
CREATE POLICY "Public Read Trailheads" ON "Trailheads" FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Trailheads" ON "Trailheads";
CREATE POLICY "Service Role Full Access Trailheads" ON "Trailheads" FOR ALL TO service_role USING (true);
