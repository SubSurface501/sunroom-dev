-- Migration: 044_fix_nodes_rls_policy.sql
-- Description: Fixes the RLS policy on the Nodes table to handle NULL project_id.

-- Drop the faulty policy
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";

-- Re-create the policy with a check for NULL project_id
CREATE POLICY "Users can view nodes of volumes they can view"
ON "Nodes" FOR SELECT
USING (
    exists (
        select 1 from "StoryVolumes" v
        where v.id = "Nodes".volume_id
        and (v.user_id = auth.uid() OR (v.project_id IS NOT NULL AND v.project_id IN (SELECT project_id FROM project_members WHERE user_id = auth.uid())))
    )
);
