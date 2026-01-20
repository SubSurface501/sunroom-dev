'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import Link from 'next/link';
import { User } from '@supabase/supabase-js';

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null); // Initialize user as null

  useEffect(() => {
    // Always fetch the latest user from the client-side session on mount
    supabase.auth.getUser().then(({ data: { user: clientUser } }) => {
        setUser(clientUser);
    });

    // Listen for changes in auth state
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user ?? null);
      if (event === 'SIGNED_OUT') {
          setUser(null); // Explicitly clear user on sign out
          router.refresh(); // Force a server component refresh in Next.js App Router
          router.push('/login');
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]); // Depend only on router

  const handleLogout = async () => {
    await supabase.auth.signOut();
    // The onAuthStateChange listener will handle updating state and redirect
  };

  // Hide Navbar on Landing Page
  if (pathname === '/') {
    return null;
  }

  return (
    <nav className="bg-gray-800 p-4 text-white flex justify-between items-center">
      <Link href="/dashboard" className="text-xl font-bold text-yellow-500 hover:text-yellow-400 transition-colors">
        The Sun Room
      </Link>
      <div className="flex items-center space-x-4">
        {user ? (
          <>
            <span className="text-gray-300 hidden sm:inline">Hello, {user.email}</span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-md text-sm font-medium transition-colors"
            >
              Logout
            </button>
          </>
        ) : (
          <Link href="/login" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium transition-colors">
            Login
          </Link>
        )}
      </div>
    </nav>
  );
}
