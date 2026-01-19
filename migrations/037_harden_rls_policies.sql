
-- Migration to harden Row Level Security (RLS) across the application.

-- 1. Harden 'Atoms' table policy
-- The original policy was missing WITH CHECK, allowing users to insert atoms for other users.
ALTER TABLE "Atoms" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can CRUD their own atoms" ON "Atoms";
CREATE POLICY "Users can perform all actions on their own atoms" ON "Atoms"
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 2. Secure 'Trailheads' table
-- This table was previously public. It should be private to the user.
ALTER TABLE "Trailheads" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public Read Trailheads" ON "Trailheads";
CREATE POLICY "Users can perform all actions on their own trailheads" ON "Trailheads"
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 3. Secure 'Sources' table
ALTER TABLE "Sources" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can perform all actions on their own sources" ON "Sources";
CREATE POLICY "Users can perform all actions on their own sources" ON "Sources"
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 4. Secure 'user_subscriptions' table
ALTER TABLE "user_subscriptions" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view their own subscription" ON "user_subscriptions";
CREATE POLICY "Users can view their own subscription" ON "user_subscriptions"
    FOR SELECT
    USING (auth.uid() = user_id);
-- Note: Inserts/Updates to subscriptions should only be handled by the backend with service_role.

-- 5. Secure 'usage_logs' table
ALTER TABLE "usage_logs" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view their own usage logs" ON "usage_logs";
CREATE POLICY "Users can view their own usage logs" ON "usage_logs"
    FOR SELECT
    USING (auth.uid() = user_id);

-- 6. Secure Graph Tables ('Nodes', 'Edges', 'Branches')
-- These tables lack a direct user_id, but are linked via volume_id. We'll secure them by checking ownership on the parent StoryVolume.
-- This requires a slightly more complex policy.

ALTER TABLE "Nodes" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can manage nodes in their own volumes" ON "Nodes";
CREATE POLICY "Users can manage nodes in their own volumes" ON "Nodes"
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM "StoryVolumes" sv
        WHERE sv.id = "Nodes".volume_id AND sv.user_id = auth.uid()
    ));

ALTER TABLE "Edges" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can manage edges in their own volumes" ON "Edges";
CREATE POLICY "Users can manage edges in their own volumes" ON "Edges"
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM "StoryVolumes" sv
        WHERE sv.id = "Edges".volume_id AND sv.user_id = auth.uid()
    ));

ALTER TABLE "Branches" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can manage branches in their own volumes" ON "Branches";
CREATE POLICY "Users can manage branches in their own volumes" ON "Branches"
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM "StoryVolumes" sv
        WHERE sv.id = "Branches".volume_id AND sv.user_id = auth.uid()
    ));

-- 7. Secure 'tiers' table
-- Tiers should be publicly readable by any authenticated user, but only modifiable by service role.
ALTER TABLE "tiers" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Authenticated users can read tiers" ON "tiers";
CREATE POLICY "Authenticated users can read tiers" ON "tiers"
    FOR SELECT
    TO authenticated
    USING (true);

DROP POLICY IF EXISTS "Service role can manage tiers" ON "tiers";
CREATE POLICY "Service role can manage tiers" ON "tiers"
    FOR ALL
    TO service_role
    USING (true);

-- Re-apply service role access for all tables as a safeguard
DROP POLICY IF EXISTS "Service Role Full Access Sources" ON "Sources";
CREATE POLICY "Service Role Full Access Sources" ON "Sources" FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Atoms" ON "Atoms";
CREATE POLICY "Service Role Full Access Atoms" ON "Atoms" FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Trailheads" ON "Trailheads";
CREATE POLICY "Service Role Full Access Trailheads" ON "Trailheads" FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service Role Full Access User Subscriptions" ON "user_subscriptions";
CREATE POLICY "Service Role Full Access User Subscriptions" ON "user_subscriptions" FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Usage Logs" ON "usage_logs";
CREATE POLICY "Service Role Full Access Usage Logs" ON "usage_logs" FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Nodes" ON "Nodes";
CREATE POLICY "Service Role Full Access Nodes" ON "Nodes" FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Edges" ON "Edges";
CREATE POLICY "Service Role Full Access Edges" ON "Edges" FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service Role Full Access Branches" ON "Branches";
CREATE POLICY "Service Role Full Access Branches" ON "Branches" FOR ALL TO service_role USING (true);

COMMIT;
