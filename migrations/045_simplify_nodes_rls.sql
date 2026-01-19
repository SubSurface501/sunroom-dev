-- Migration: 045_simplify_nodes_rls.sql
-- Description: Simplifies the RLS policy on the Nodes table to only check for user_id.

-- Drop the faulty policy
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";

-- Re-create a simplified policy
CREATE POLICY "Users can view nodes of volumes they own"
ON "Nodes" FOR SELECT
USING (
    exists (
        select 1 from "StoryVolumes" v
        where v.id = "Nodes".volume_id
        and (v.user_id = auth.uid())
    )
);
