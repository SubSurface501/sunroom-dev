'use client';

import React from 'react';
import { useAuth } from './AuthContext';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    // If not loading and no user, redirect to login
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  // While loading, show a spinner
  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-950">
        <Loader2 className="h-12 w-12 animate-spin text-purple-400" />
      </div>
    );
  }

  // If there's a user, show the page
  if (user) {
    return <>{children}</>;
  }

  // If no user and not loading (during the brief moment before redirect), show nothing or a loader
  return (
    <div className="flex h-screen w-full items-center justify-center bg-gray-950">
        <Loader2 className="h-12 w-12 animate-spin text-purple-400" />
    </div>
  );
};

export default ProtectedRoute;
