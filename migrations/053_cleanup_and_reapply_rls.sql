-- Migration: 053_cleanup_and_reapply_rls.sql
-- Description: Cleans up existing RLS policies and functions, then reapplies them in the correct order.

-- 1. Drop policies that depend on get_my_projects() function
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";
DROP POLICY IF EXISTS "Members can view project roster" ON public.project_members;

-- 2. Drop get_my_projects() function
DROP FUNCTION IF EXISTS get_my_projects();

-- 3. Re-create the function to get user's projects
CREATE OR REPLACE FUNCTION get_my_projects()
RETURNS TABLE(project_id uuid)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  IF auth.uid() IS NOT NULL THEN
    RETURN QUERY SELECT pm.project_id FROM public.project_members pm WHERE pm.user_id = auth.uid();
  END IF;
END;
$$;

-- 4. Re-create the project_members policy using the function
ALTER TABLE public.project_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Members can view project roster"
ON public.project_members
FOR SELECT
USING (
  (auth.uid() IS NOT NULL) AND project_id IN (SELECT project_id FROM get_my_projects())
);

-- 5. Re-create the Nodes policy with the auth.uid() non-null check
ALTER TABLE "Nodes" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view nodes of volumes they can view"
ON "Nodes" FOR SELECT
USING (
    (auth.uid() IS NOT NULL) AND
    exists (
        select 1 from "StoryVolumes" v
        where v.id = "Nodes".volume_id
        and (
            v.user_id = auth.uid()
            OR
            (v.project_id IS NOT NULL AND v.project_id IN (SELECT project_id FROM get_my_projects()))
        )
    )
);

-- 6. Ensure other RLS policies from 037_harden_rls_policies.sql and other migrations are correctly applied for Nodes
DROP POLICY IF EXISTS "Users can manage nodes in their own volumes" ON "Nodes";
CREATE POLICY "Users can manage nodes in their own volumes" ON "Nodes"
    AS PERMISSIVE FOR ALL
    TO authenticated
    USING (
        exists (
            select 1 from "StoryVolumes" sv
            where sv.id = "Nodes".volume_id AND sv.user_id = auth.uid()
        )
    )
    WITH CHECK (
        exists (
            select 1 from "StoryVolumes" sv
            where sv.id = "Nodes".volume_id AND sv.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Service Role Full Access Nodes" ON "Nodes";
CREATE POLICY "Service Role Full Access Nodes" ON "Nodes" FOR ALL TO service_role USING (true);
