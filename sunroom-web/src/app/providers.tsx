'use client';

import { WorkspaceProvider } from '@/context/WorkspaceContext';
import { AuthProvider } from '@/components/AuthContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <WorkspaceProvider>
        {children}
      </WorkspaceProvider>
    </AuthProvider>
  );
}
