-- Migration: 046_revert_simplified_rls.sql
-- Description: Drops the simplified RLS policy on the Nodes table.

-- Drop the simplified policy
DROP POLICY IF EXISTS "Users can view nodes of volumes they own" ON "Nodes";
