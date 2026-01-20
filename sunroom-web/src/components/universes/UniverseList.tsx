'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/components/AuthContext';
import { Universe, getUniverses, createUniverse } from '@/services/universeService';
import { PlusCircle, Globe } from 'lucide-react';

interface UniverseListProps {
  onSelectUniverse: (universeId: string | null, activeEpochId: number | null) => void;
}

export const UniverseList: React.FC<UniverseListProps> = ({ onSelectUniverse }) => {
  const { session } = useAuth();
  const [universes, setUniverses] = useState<Universe[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newUniverseName, setNewUniverseName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  const fetchUniverses = async () => {
    if (!session) return;
    setIsLoading(true);
    setError(null);
    try {
      const fetchedUniverses = await getUniverses(session.access_token);
      setUniverses(fetchedUniverses);
    } catch (err) {
      console.error("Failed to fetch universes:", err);
      setError("Failed to load universes.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUniverses();
  }, [session]);

  const handleCreateUniverse = async () => {
    if (!session || !newUniverseName.trim()) return;
    setIsLoading(true);
    try {
      const newUniverse = await createUniverse(session.access_token, { name: newUniverseName });
      setUniverses((prev) => [...prev, newUniverse]);
      setNewUniverseName('');
      setShowCreateForm(false);
      onSelectUniverse(newUniverse.id, newUniverse.active_epoch_id || null); // Pass active_epoch_id
    } catch (err) {
      console.error("Failed to create universe:", err);
      setError("Failed to create universe.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <div className="text-gray-400">Loading universes...</div>;
  }

  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  return (
    <div>
      <button 
        onClick={() => setShowCreateForm(!showCreateForm)}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 mb-4 bg-purple-600 hover:bg-purple-700 rounded-md text-white font-medium transition-colors"
      >
        <PlusCircle size={16} /> New Universe
      </button>

      {showCreateForm && (
        <div className="mb-4 p-3 bg-gray-800 rounded-md">
          <input
            type="text"
            placeholder="Universe Name"
            value={newUniverseName}
            onChange={(e) => setNewUniverseName(e.target.value)}
            className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white mb-2"
          />
          <button 
            onClick={handleCreateUniverse}
            disabled={!newUniverseName.trim()}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-white font-medium transition-colors disabled:opacity-50"
          >
            Create
          </button>
        </div>
      )}

      {universes.length === 0 ? (
        <p className="text-gray-500 text-center">No universes created yet.</p>
      ) : (
        <ul className="space-y-2">
          {universes.map((universe) => (
            <li key={universe.id}>
              <button
                onClick={() => onSelectUniverse(universe.id, universe.active_epoch_id || null)} // Pass active_epoch_id
                className="w-full text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-md flex items-center gap-2 transition-colors"
              >
                <Globe size={16} className="text-blue-400" />
                {universe.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
