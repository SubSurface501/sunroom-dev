'use client';

import React, { useState, useEffect } from 'react';
import { Universe, Archetype, Epoch, updateEpoch } from '@/services/universeService';
import { useAuth } from '@/components/AuthContext';
import { AlertTriangle, CheckCircle, Lightbulb, Edit, X, Save } from 'lucide-react';

interface ArchetypeCardProps {
  universe: Universe;
  archetypes: Archetype[];
  onUniverseUpdate: (updatedUniverse: Universe) => void;
  currentActiveEpoch: Epoch | null;
}

export const ArchetypeCard: React.FC<ArchetypeCardProps> = ({ universe, archetypes, onUniverseUpdate, currentActiveEpoch }) => {
  const { session } = useAuth();
  const [selectedArchetypeId, setSelectedArchetypeId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showCustomProhibitionsEditor, setShowCustomProhibitionsEditor] = useState(false);
  const [customProhibitions, setCustomProhibitions] = useState<string[]>([]);
  const [newProhibition, setNewProhibition] = useState('');

  const activeArchetype = currentActiveEpoch?.archetype 
    ? archetypes.find(a => a.name.toLowerCase() === currentActiveEpoch.archetype?.toLowerCase()) 
    : undefined;

  useEffect(() => {
    if (currentActiveEpoch?.archetype) {
      setSelectedArchetypeId(currentActiveEpoch.archetype.toLowerCase());
    } else {
      setSelectedArchetypeId(undefined);
    }
    setCustomProhibitions(currentActiveEpoch?.prohibitions || []);
  }, [currentActiveEpoch]);

  const handleArchetypeChange = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    if (!session || !currentActiveEpoch?.id) return;

    const newArchetypeId = event.target.value;
    setSelectedArchetypeId(newArchetypeId);
    setFeedback(null);
    setIsLoading(true);

    try {
      const updatedEpoch = await updateEpoch(session.access_token, currentActiveEpoch.id, {
        archetype: newArchetypeId,
      });
      onUniverseUpdate({ ...universe, active_epoch_id: updatedEpoch.id });
      setFeedback(`Archetype updated to '${updatedEpoch.archetype}'.`);
    } catch (err) {
      console.error("Failed to update archetype:", err);
      setFeedback("Failed to update archetype.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleProhibitionAdd = () => {
    if (newProhibition.trim() && !customProhibitions.some(p => p.toLowerCase() === newProhibition.trim().toLowerCase())) {
      setCustomProhibitions((prev) => [...prev, newProhibition.trim()]);
      setNewProhibition('');
    }
  };

  const handleProhibitionRemove = (prohibitionToRemove: string) => {
    setCustomProhibitions((prev) => prev.filter((p) => p !== prohibitionToRemove));
  };

  const handleSaveCustomProhibitions = async () => {
    if (!session || !currentActiveEpoch?.id) return;
    setIsLoading(true);
    setFeedback(null);

    try {
      await updateEpoch(session.access_token, currentActiveEpoch.id, {
        prohibitions: customProhibitions,
      });
      setFeedback("Custom prohibitions saved.");
      setShowCustomProhibitionsEditor(false);
    } catch (err) {
      console.error("Failed to save custom prohibitions:", err);
      setFeedback("Failed to save custom prohibitions.");
    } finally {
      setIsLoading(false);
    }
  };

  const displayProhibitions = activeArchetype?.prohibitions || [];
  const combinedProhibitions = Array.from(new Set([...displayProhibitions, ...customProhibitions]));
  const displaySuggestions = activeArchetype?.suggestions || [];

  return (
    <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700">
      <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
        <Lightbulb size={20} className="text-yellow-400" /> Active Archetype
      </h3>

      <div className="mb-4">
        <label htmlFor="archetype-select" className="block text-sm font-medium text-gray-300 mb-2">
          Select Active Archetype for Current Epoch:
        </label>
        <select
          id="archetype-select"
          value={selectedArchetypeId || ''}
          onChange={handleArchetypeChange}
          className="w-full bg-gray-950 border border-gray-700 rounded-md p-2 text-white disabled:opacity-50"
          disabled={isLoading || !currentActiveEpoch}
        >
          <option value="" disabled>-- Select an Archetype --</option>
          {archetypes.map((arch) => (
            <option key={arch.name.toLowerCase()} value={arch.name.toLowerCase()}>
              {arch.name}
            </option>
          ))}
        </select>
      </div>

      {currentActiveEpoch && activeArchetype && (
        <div className="space-y-4">
          <p className="text-gray-300 text-sm"><strong>Description:</strong> {activeArchetype.description}</p>
          <p className="text-gray-300 text-sm italic"><strong>System Anchor:</strong> {activeArchetype.system_anchor}</p>

          {combinedProhibitions.length > 0 && (
            <div>
              <h4 className="text-md font-semibold text-red-400 mb-2 flex items-center gap-1">
                <AlertTriangle size={16} /> Banned Concepts (Current Epoch):
              </h4>
              <div className="flex flex-wrap gap-2">
                {combinedProhibitions.map((p) => (
                  <span key={p} className="text-red-300 bg-red-800/30 px-3 py-1 rounded-full text-xs line-through border border-red-500/20">
                    {p}
                  </span>
                ))}
              </div>
              <button
                onClick={() => setShowCustomProhibitionsEditor(!showCustomProhibitionsEditor)}
                className="mt-3 inline-flex items-center px-3 py-1 text-xs font-medium text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/10 transition-colors"
                disabled={isLoading}
              >
                <Edit size={14} className="mr-1" /> {showCustomProhibitionsEditor ? 'Hide Editor' : 'Edit Custom Laws'}
              </button>

              {showCustomProhibitionsEditor && (
                <div className="mt-4 p-3 bg-gray-900/50 rounded-md border border-gray-700">
                  <h5 className="text-xs font-bold text-gray-400 uppercase mb-2">Custom Prohibitions:</h5>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {customProhibitions.map((p) => (
                      <span key={`custom-${p}`} className="text-red-300 bg-red-800/30 px-3 py-1 rounded-full text-xs flex items-center gap-1">
                        {p}
                        <button onClick={() => handleProhibitionRemove(p)} className="text-red-200 hover:text-white"><X size={12} /></button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Add new banned concept"
                      value={newProhibition}
                      onChange={(e) => setNewProhibition(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleProhibitionAdd(); } }}
                      className="flex-grow bg-gray-950 border border-gray-600 rounded p-2 text-white text-sm"
                      disabled={isLoading}
                    />
                    <button
                      onClick={handleProhibitionAdd}
                      disabled={isLoading || !newProhibition.trim()}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-md text-white font-medium transition-colors text-sm disabled:opacity-50"
                    >
                      Add
                    </button>
                  </div>
                  <button
                    onClick={handleSaveCustomProhibitions}
                    disabled={isLoading}
                    className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-md text-white font-medium transition-colors disabled:opacity-50"
                  >
                    <Save size={16} /> {isLoading ? 'Saving...' : 'Save Custom Laws'}
                  </button>
                </div>
              )}
            </div>
          )}

          {displaySuggestions.length > 0 && (
            <div>
              <h4 className="text-md font-semibold text-green-400 mb-2 flex items-center gap-1">
                <CheckCircle size={16} /> Suggested Concepts:
              </h4>
              <div className="flex flex-wrap gap-2">
                {displaySuggestions.map((s) => (
                  <span key={s} className="text-green-300 bg-green-800/30 px-3 py-1 rounded-full text-xs border border-green-500/20">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {feedback && <p className="text-xs text-blue-400 mt-4">{feedback}</p>}
    </div>
  );
};