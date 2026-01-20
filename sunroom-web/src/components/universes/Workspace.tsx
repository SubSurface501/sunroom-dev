'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/components/AuthContext';
import { Universe, Archetype, Epoch, Atom, getUniverse, getArchetypes, getEpochs, getAtomsForUniverse, unlockAtom } from '@/services/universeService';
import { Loader2, BookText, Clock, Archive, CheckCircle } from 'lucide-react';
import { ArchetypeCard } from './ArchetypeCard'; 
import { EpochTimeline } from './EpochTimeline'; 

interface WorkspaceProps {
  universeId: string | null;
}

export const Workspace: React.FC<WorkspaceProps> = ({ universeId }) => {
  const { session } = useAuth();
  const [universe, setUniverse] = useState<Universe | null>(null);
  const [archetypes, setArchetypes] = useState<Archetype[]>([]);
  const [epochs, setEpochs] = useState<Epoch[]>([]);
  const [atoms, setAtoms] = useState<Atom[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchArchetypes = useCallback(async () => {
    try {
      const fetchedArchetypes = await getArchetypes();
      setArchetypes(fetchedArchetypes);
    } catch (err) {
      console.error("Failed to fetch archetypes:", err);
      setError("Failed to load archetypes.");
    }
  }, []);

  const fetchUniverseData = useCallback(async (id: string) => {
    if (!session) return;
    setIsLoading(true);
    setError(null);
    try {
      const fetchedUniverse = await getUniverse(session.access_token, id);
      setUniverse(fetchedUniverse);

      const fetchedEpochs = await getEpochs(session.access_token, id);
      setEpochs(fetchedEpochs);

      const fetchedAtoms = await getAtomsForUniverse(session.access_token, id);
      setAtoms(fetchedAtoms);

    } catch (err) {
      console.error("Failed to fetch universe data:", err);
      setError("Failed to load universe data.");
    } finally {
      setIsLoading(false);
    }
  }, [session]);

  useEffect(() => {
    fetchArchetypes();
  }, [fetchArchetypes]);

  useEffect(() => {
    if (universeId) {
      fetchUniverseData(universeId);
    } else {
      setUniverse(null);
      setEpochs([]);
      setAtoms([]);
      setIsLoading(false);
    }
  }, [universeId, fetchUniverseData]);

  // --- NEW: THE UNLOCK HANDLER ---
  const handleUnlockAtom = async (atomId: string) => {
    if (!session || !universe?.id || !currentActiveEpoch?.id) return;

    setIsLoading(true);
    try {
      // Set the atom's discovery_epoch_id to the current active epoch's ID
      await unlockAtom(session.access_token, atomId, currentActiveEpoch.id);
      
      // Re-fetch all data to refresh the "Active" and "Latent" lists instantly
      await fetchUniverseData(universe.id);
      console.info(`[Discovery] Atom ${atomId} promoted to current epoch.`);
    } catch (err) {
      console.error("Failed to unlock lore atom:", err);
      setError("Failed to reveal latent lore.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUniverseUpdate = (updatedUniverse: Universe) => {
    setUniverse(updatedUniverse);
    if (updatedUniverse.id) {
        fetchUniverseData(updatedUniverse.id); 
    }
  };

  const currentActiveEpoch = (universe?.active_epoch_id 
    ? epochs.find(epoch => epoch.id === universe.active_epoch_id)
    : null) || null;

  if (!universeId) {
    return (
      <div className="text-gray-400 p-4 text-center">
        Select a universe from the left to view its blueprint, or create a new one.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 text-blue-400">
        <Loader2 className="animate-spin mr-2" size={24} />
        Synchronizing Reality...
      </div>
    );
  }

  if (error) {
    return <div className="text-red-500 p-4">Error: {error}</div>;
  }

  if (!universe) {
    return <div className="text-gray-400 p-4 text-center">Universe not found.</div>;
  }

  const activeAtoms = atoms.filter(atom => 
    !atom.discovery_epoch_id || 
    (currentActiveEpoch && atom.discovery_epoch_id <= currentActiveEpoch.id)
  ).sort((a, b) => (a.name || '').localeCompare(b.name || ''));

  const latentAtoms = atoms.filter(atom => 
    atom.discovery_epoch_id && 
    (currentActiveEpoch ? atom.discovery_epoch_id > currentActiveEpoch.id : true)
  ).sort((a, b) => (a.name || '').localeCompare(b.name || ''));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-1">Universe Blueprint: {universe.name}</h2>
        <p className="text-gray-500 text-sm font-mono">UUID: {universe.id}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Column 1: The Bible (Archetype) */}
        <div className="space-y-4">
          <h3 className="text-xl font-semibold flex items-center gap-2 text-purple-400">
            <BookText size={20} /> The Bible
          </h3>
          <ArchetypeCard 
            universe={universe} 
            archetypes={archetypes} 
            onUniverseUpdate={handleUniverseUpdate}
            currentActiveEpoch={currentActiveEpoch}
          />
        </div>
        
        {/* Column 2: The Timeline (Epochs) */}
        <div className="space-y-4">
          <h3 className="text-xl font-semibold flex items-center gap-2 text-blue-400">
            <Clock size={20} /> The Timeline
          </h3>
          <EpochTimeline 
            universe={universe} 
            epochs={epochs} 
            archetypes={archetypes}
            onUniverseUpdate={handleUniverseUpdate} 
            onEpochsUpdate={() => fetchUniverseData(universe.id)} 
          />
        </div>

        {/* Column 3: The Archives (Lore Browser) */}
        <div className="space-y-4">
          <h3 className="text-xl font-semibold flex items-center gap-2 text-yellow-400">
            <Archive size={20} /> The Archives
          </h3>
          <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 min-h-[300px] max-h-[700px] overflow-y-auto custom-scrollbar">
            {atoms.length === 0 ? (
              <p className="text-gray-500 text-center italic">No lore indexed for this world.</p>
            ) : (
              <div className="space-y-6">
                {activeAtoms.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-widest text-green-500 mb-3">Active Canon</h4>
                    <ul className="space-y-2">
                      {activeAtoms.map(atom => (
                        <li key={atom.id} className="text-gray-300 text-sm flex items-center gap-2 p-2 bg-gray-800/40 rounded border border-gray-700/50">
                          <CheckCircle size={14} className="text-green-500" />
                          <div className="flex flex-col">
                            <span className="font-medium">{atom.name}</span>
                            <span className="text-[10px] text-gray-500 uppercase">{atom.type}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {latentAtoms.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-widest text-yellow-500 mb-3">Lore Reservoir</h4>
                    <p className="text-[10px] text-gray-500 mb-3">Hidden from the AI until the discovery epoch is reached.</p>
                    <ul className="space-y-2">
                      {latentAtoms.map(atom => (
                        <li key={atom.id} className="text-gray-300 text-sm flex items-center justify-between p-2 bg-gray-800/40 rounded border border-yellow-900/20">
                          <div className="flex items-center gap-2">
                            <Archive size={14} className="text-yellow-600" />
                            <div className="flex flex-col">
                                <span className="font-medium">{atom.name}</span>
                                <span className="text-[10px] text-gray-500 uppercase italic">Unlocks at Epoch {atom.discovery_epoch_id}</span>
                            </div>
                          </div>
                          <button 
                            onClick={() => handleUnlockAtom(atom.id)} 
                            className="ml-4 px-2 py-1 bg-green-600/20 hover:bg-green-600 text-green-400 hover:text-white border border-green-600/30 rounded text-[10px] font-bold uppercase transition-all"
                            disabled={isLoading || !currentActiveEpoch}
                            title="Reveal now in current epoch"
                          >
                            Reveal
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};