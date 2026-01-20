import React, { createContext, useContext, useState, ReactNode } from 'react';

export type WorkspaceMode = 'personal' | 'project';

interface WorkspaceState {
  mode: WorkspaceMode;
  projectId: string | null;
  projectName: string | null;
  setWorkspace: (mode: WorkspaceMode, projectId?: string | null, projectName?: string | null) => void;
}

const WorkspaceContext = createContext<WorkspaceState | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<WorkspaceMode>('personal');
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string | null>(null);

  const setWorkspace = (newMode: WorkspaceMode, newProjectId: string | null = null, newProjectName: string | null = null) => {
    setMode(newMode);
    setProjectId(newProjectId);
    setProjectName(newProjectName);
  };

  return (
    <WorkspaceContext.Provider value={{ mode, projectId, projectName, setWorkspace }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
