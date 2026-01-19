-- Migration: 049_fix_project_members_rls.sql
-- Description: Implements a non-recursive RLS policy for project_members to fix 500 errors.

-- 1. Drop the temporary disabling of RLS if it's still there
ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;

-- 2. Drop the old faulty policy if it exists
DROP POLICY IF EXISTS "Members can view project roster" ON project_members;

-- 3. Create a function to get the projects for the current user.
--    Using a SECURITY DEFINER function is a standard way to break RLS recursion.
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

-- 4. Create the new, non-recursive policy using the function
CREATE POLICY "Members can view project roster"
ON public.project_members
FOR SELECT
USING (
  project_id IN (SELECT project_id FROM get_my_projects())
);

-- 5. Restore the original Nodes policy now that the underlying issue is fixed.
--    This ensures that the Nodes table is also secure.
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";
CREATE POLICY "Users can view nodes of volumes they can view"
ON "Nodes" FOR SELECT
USING (
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

