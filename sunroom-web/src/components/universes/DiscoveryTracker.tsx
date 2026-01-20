'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/components/AuthContext';
import { getLatentAtomCount } from '@/services/universeService';
import { Lock } from 'lucide-react';

interface DiscoveryTrackerProps {
  universeId: string | null;
  activeEpochId?: number | null;
}

export const DiscoveryTracker: React.FC<DiscoveryTrackerProps> = ({ universeId, activeEpochId }) => {
  const { session } = useAuth();
  const [latentAtomCount, setLatentAtomCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLatentCount = async () => {
      if (!universeId || !session) {
        setLatentAtomCount(0);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const data = await getLatentAtomCount(session.access_token, universeId);
        setLatentAtomCount(data.latent_atom_count);
      } catch (err) {
        console.error("Failed to fetch latent atom count:", err);
        setError("Failed to load latent lore count.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchLatentCount();
  }, [universeId, session, activeEpochId]); // Re-fetch if activeEpochId changes

  if (!universeId || isLoading) {
    return null; // Don't show if no universe selected or loading
  }

  if (error) {
    return <div className="text-red-500 text-sm">Error: {error}</div>;
  }

  return (
    <div className="mt-4 p-3 bg-gray-800 rounded-md flex items-center gap-2 text-sm text-gray-300">
      <Lock size={16} className="text-yellow-500" /> 
      <span className="font-semibold">Lore Reservoir:</span> 
      <span>{latentAtomCount} atoms locked</span>
    </div>
  );
};
