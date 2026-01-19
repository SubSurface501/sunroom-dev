-- Migration: 051_final_nodes_rls_fix.sql
-- Description: Implements the final, robust RLS policy on the Nodes table, checking for a non-null auth.uid().

-- 1. Drop the temporary permissive policy
DROP POLICY IF EXISTS "TEMP - Permissive view all nodes" ON "Nodes";

-- 2. Drop the function and policy for project_members to re-create them cleanly
DROP POLICY IF EXISTS "Members can view project roster" ON public.project_members;
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
CREATE POLICY "Members can view project roster"
ON public.project_members
FOR SELECT
USING (
  (auth.uid() IS NOT NULL) AND project_id IN (SELECT project_id FROM get_my_projects())
);
ALTER TABLE public.project_members ENABLE ROW LEVEL SECURITY;


-- 5. Re-create the Nodes policy with the auth.uid() non-null check
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";
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
