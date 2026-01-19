-- Migration: 052_revert_nodes_rls_to_user_only.sql
-- Description: Reverts the Nodes RLS policy to only check for user_id, temporarily disabling project-based access, to debug the recurring 500 error.

-- Drop existing Nodes policy
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";

-- Re-create the simplified policy for Nodes
CREATE POLICY "Users can view nodes of volumes they own"
ON "Nodes" FOR SELECT
USING (
    exists (
        select 1 from "StoryVolumes" v
        where v.id = "Nodes".volume_id
        and (v.user_id = auth.uid())
    )
);
