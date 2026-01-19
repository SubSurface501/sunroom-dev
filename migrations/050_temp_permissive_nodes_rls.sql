-- Migration: 050_temp_permissive_nodes_rls.sql
-- Description: Temporarily makes the RLS policy on the Nodes table permissive for ALL users (public).
-- This is for debugging purposes to isolate issues related to auth.uid().

-- Drop any existing policy on Nodes
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";
DROP POLICY IF EXISTS "Users can view nodes of volumes they own" ON "Nodes";


-- Create a new permissive policy for SELECT operations
CREATE POLICY "TEMP - Permissive view all nodes"
ON "Nodes" FOR SELECT
USING (true);
