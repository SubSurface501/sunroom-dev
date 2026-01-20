'use client';

import React, { useState } from 'react';
import { UniverseList } from '@/components/universes/UniverseList';
import { Workspace } from '@/components/universes/Workspace';
import { DiscoveryTracker } from '@/components/universes/DiscoveryTracker'; // Import DiscoveryTracker

const UniversesPage = () => {
  const [selectedUniverseId, setSelectedUniverseId] = useState<string | null>(null);
  const [selectedUniverseActiveEpochId, setSelectedUniverseActiveEpochId] = useState<number | null>(null);

  const handleSelectUniverse = (universeId: string | null, activeEpochId: number | null) => {
    setSelectedUniverseId(universeId);
    setSelectedUniverseActiveEpochId(activeEpochId);
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white">
      {/* Column 1: Universe Rail */}
      <aside className="w-1/4 min-w-[300px] bg-gray-900 p-4 border-r border-gray-800">
        <h2 className="text-xl font-bold mb-4">Universes</h2>
        <div className="p-2 bg-gray-800 rounded-md">
            <UniverseList onSelectUniverse={handleSelectUniverse} />
            {selectedUniverseId && (
              <DiscoveryTracker 
                universeId={selectedUniverseId} 
                activeEpochId={selectedUniverseActiveEpochId} 
              />
            )}
        </div>
      </aside>

      {/* Column 2: Workspace */}
      <main className="flex-1 p-8 overflow-y-auto">
        <h1 className="text-3xl font-bold mb-2">Multiverse Control Center</h1>
        <p className="text-gray-400 mb-8">Define the fundamental laws of your worlds and manage their evolution.</p>
        
        <div className="p-4 bg-gray-900 rounded-lg">
             <Workspace universeId={selectedUniverseId} />
        </div>
      </main>
    </div>
  );
};

export default UniversesPage;
