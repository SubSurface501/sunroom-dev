-- Migration: 035_add_branch_id_to_nodes.sql
-- Description: Adds branch_id to Nodes table to support branching timelines.

ALTER TABLE "Nodes" ADD COLUMN IF NOT EXISTS branch_id uuid REFERENCES "Branches"(id);
CREATE INDEX IF NOT EXISTS idx_nodes_branch ON "Nodes"(branch_id);
