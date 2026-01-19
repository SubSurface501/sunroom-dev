-- Migration: 048_temp_disable_project_members_rls.sql
-- Description: Temporarily disable RLS on project_members table for debugging purposes.

-- Disable the existing policy
DROP POLICY IF EXISTS "Members can view project roster" ON project_members;
ALTER TABLE project_members DISABLE ROW LEVEL SECURITY;
