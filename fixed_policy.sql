-- This policy fixes the infinite recursion bug.
DROP POLICY IF EXISTS "Members can view project roster" ON project_members;
CREATE POLICY "Members can view project roster" ON project_members
    FOR SELECT USING (
        project_id IN (
            SELECT my_projects.project_id FROM project_members my_projects WHERE my_projects.user_id = auth.uid()
        )
    );
