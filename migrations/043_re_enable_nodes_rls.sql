-- Migration: 043_re_enable_nodes_rls.sql
-- Description: Re-enables the original RLS policy on the Nodes table.

-- Drop the temporary policy
DROP POLICY IF EXISTS "TEMP - Users can view all nodes" ON "Nodes";

-- Re-create the original policy from 034_normalize_graph_schema.sql
CREATE POLICY "Users can view nodes of volumes they can view"
ON "Nodes" FOR SELECT
USING (
    exists (
        select 1 from "StoryVolumes" v
        where v.id = "Nodes".volume_id
        and (v.user_id = auth.uid() or v.project_id in (select project_id from project_members where user_id = auth.uid()))
    )
);
