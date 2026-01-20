'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function TestConnection() {
  const [status, setStatus] = useState('Testing...');
  const [error, setError] = useState('');

  useEffect(() => {
    async function test() {
      try {
        console.log("Testing generic fetch...");
        const { data, error } = await supabase.from('StoryVolumes').select('count', { count: 'exact', head: true });
        
        if (error) {
            console.error("DB Error:", error);
            setError(error.message);
            setStatus('Failed');
        } else {
            console.log("DB Success:", data);
            setStatus('Success! Connected to DB.');
        }
      } catch (e: any) {
          console.error("Fetch Exception:", e);
          setError(e.message);
          setStatus('Exception');
      }
    }
    test();
  }, []);

  return (
    <div className="p-10 bg-gray-900 text-white h-screen">
      <h1>Connection Test</h1>
      <p>Status: {status}</p>
      {error && <p className="text-red-500">{error}</p>}
    </div>
  );
}
