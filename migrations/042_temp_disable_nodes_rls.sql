-- Migration: 042_temp_disable_nodes_rls.sql
-- Description: Temporarily disable RLS on Nodes table for debugging purposes.

-- Disable the existing policy
DROP POLICY IF EXISTS "Users can view nodes of volumes they can view" ON "Nodes";

-- Create a temporary permissive policy for authenticated users
CREATE POLICY "TEMP - Users can view all nodes" ON "Nodes"
FOR SELECT
TO authenticated
USING (true);
