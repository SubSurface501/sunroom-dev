-- This script fixes the RLS policies related to the 'Collective' feature.
-- It is safe to run multiple times.

-- 1. Fix Projects Policies
DROP POLICY IF EXISTS "Users can view projects they are members of" ON projects;
CREATE POLICY "Users can view projects they are members of" ON projects
    FOR SELECT USING (
        auth.uid() = owner_id OR 
        EXISTS (SELECT 1 FROM project_members WHERE project_id = projects.id AND user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can create projects" ON projects;
CREATE POLICY "Users can create projects" ON projects
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

-- 2. Fix Project Members Policies (The root cause of the infinite recursion)
DROP POLICY IF EXISTS "Members can view project roster" ON project_members;
CREATE POLICY "Members can view project roster" ON project_members
    FOR SELECT USING (
        project_id IN (
            SELECT my_projects.project_id FROM project_members my_projects WHERE my_projects.user_id = auth.uid()
        )
    );
