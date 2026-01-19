-- Migration: 054_set_rls_for_supabase_debugging.sql
-- Description: Sets up specific RLS policies for debugging a persistent 500 error.
-- Nodes RLS: user-only access.
-- Project Members RLS: permissive for authenticated users.

-- Clean up existing policies and function first
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";
DROP POLICY IF EXISTS "Users can view nodes of volumes they own" ON "Nodes";
DROP POLICY IF EXISTS "TEMP - Permissive view all nodes" ON "Nodes";

DROP POLICY IF EXISTS "Members can view project roster" ON public.project_members;
DROP FUNCTION IF EXISTS get_my_projects();

-- Re-create the get_my_projects() function (needed for Nodes policy, even simplified)
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

-- Set Nodes RLS to user-only access (known to avoid 500 initially)
ALTER TABLE "Nodes" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view nodes of volumes they own"
ON "Nodes" FOR SELECT
USING (
    exists (
        select 1 from "StoryVolumes" v
        where v.id = "Nodes".volume_id
        and (v.user_id = auth.uid())
    )
);

-- Set project_members RLS to be permissive for authenticated users
ALTER TABLE public.project_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Permissive project_members for authenticated"
ON public.project_members
FOR SELECT
USING (auth.uid() IS NOT NULL);
