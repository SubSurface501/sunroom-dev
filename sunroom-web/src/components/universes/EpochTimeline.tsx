'use client';

import React, { useState } from 'react';
import { Universe, Epoch, Archetype, createEpoch, updateUniverse, updateEpoch } from '@/services/universeService';
import { useAuth } from '@/components/AuthContext';
import { PlusCircle, Clock, CheckCircle, Sparkles } from 'lucide-react'; // Added Sparkles icon

interface EpochTimelineProps {
  universe: Universe;
  epochs: Epoch[];
  archetypes: Archetype[];
  onUniverseUpdate: (updatedUniverse: Universe) => void;
  onEpochsUpdate: () => void; // Callback to refresh epochs after creation/update
}

export const EpochTimeline: React.FC<EpochTimelineProps> = ({ universe, epochs, archetypes, onUniverseUpdate, onEpochsUpdate }) => {
  const { session } = useAuth();
  const [isCreatingEpoch, setIsCreatingEpoch] = useState(false);
  const [newEpochName, setNewEpochName] = useState('');
  const [newEpochArchetype, setNewEpochArchetype] = useState<string | undefined>(undefined);
  
  // State for editing existing epochs
  const [editingEpochId, setEditingEpochId] = useState<number | null>(null);
  const [editSeedProse, setEditSeedProse] = useState('');
  const [editCharacterStances, setEditCharacterStances] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showAnimation, setShowAnimation] = useState(false);
  const [animationMessage, setAnimationMessage] = useState('');

  const triggerAnimation = (message: string) => {
    setAnimationMessage(message);
    setShowAnimation(true);
    setTimeout(() => {
      setShowAnimation(false);
      setAnimationMessage('');
    }, 4000); // Animation visible for 4 seconds
  };

  const handleStartEdit = (epoch: Epoch) => {
    setEditingEpochId(epoch.id);
    setEditSeedProse(epoch.seed_prose || '');
    setEditCharacterStances(JSON.stringify(epoch.character_stances || {}, null, 2));
  };

  const handleCancelEdit = () => {
    setEditingEpochId(null);
    setEditSeedProse('');
    setEditCharacterStances('');
  };

  const handleSaveEpochDetails = async (epochId: number) => {
    if (!session || !universe.id) return;
    setIsLoading(true);
    try {
      let parsedStances = {};
      try {
        parsedStances = JSON.parse(editCharacterStances);
      } catch (e) {
        alert("Invalid JSON for Character Stances. Please fix syntax.");
        setIsLoading(false);
        return;
      }

      await updateEpoch(session.access_token, epochId, {
        seed_prose: editSeedProse,
        character_stances: parsedStances
      });

      const msg = "Epoch Narrative Data Locked.";
      setFeedback(msg);
      triggerAnimation(msg);
      onEpochsUpdate();
      setEditingEpochId(null);
    } catch (err) {
      console.error("Failed to update epoch details:", err);
      setFeedback("Failed to save details.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateEpoch = async () => {
    if (!session || !universe.id || !newEpochName.trim() || !newEpochArchetype) return;

    setIsLoading(true);
    setFeedback(null);

    try {
      const createdEpoch = await createEpoch(session.access_token, universe.id, {
        name: newEpochName,
        archetype: newEpochArchetype,
      });

      // Automatically set the new epoch as active for the universe
      await updateUniverse(session.access_token, universe.id, { active_epoch_id: createdEpoch.id });
      
      setNewEpochName('');
      setNewEpochArchetype(undefined);
      setIsCreatingEpoch(false);
      const msg = `Epoch '${createdEpoch.name}' created and activated. Reality Shift initiated!`;
      setFeedback(msg);
      triggerAnimation(msg);
      onEpochsUpdate(); // Refresh the list of epochs in Workspace
      onUniverseUpdate({ ...universe, active_epoch_id: createdEpoch.id }); // Update parent universe state

    } catch (err) {
      console.error("Failed to create epoch:", err);
      setFeedback("Failed to create new epoch.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivateEpoch = async (epochId: number) => {
    if (!session || !universe.id) return;
    setIsLoading(true);
    setFeedback(null);

    try {
      await updateUniverse(session.access_token, universe.id, { active_epoch_id: epochId });
      const activatedEpochName = epochs.find(e => e.id === epochId)?.name;
      const msg = `Epoch '${activatedEpochName}' activated. Reality Shift initiated!`;
      setFeedback(msg);
      triggerAnimation(msg);
      onUniverseUpdate({ ...universe, active_epoch_id: epochId });
    } catch (err) {
      console.error("Failed to activate epoch:", err);
      setFeedback("Failed to activate epoch.");
    } finally {
      setIsLoading(false);
    }
  };

  // Sort epochs by ID for consistent timeline display (assuming ID is sequential)
  const sortedEpochs = [...epochs].sort((a, b) => a.id - b.id);

  return (
    <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700 h-full flex flex-col">
      <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
        <Clock size={20} className="text-blue-400" /> Epoch Timeline
      </h3>

      <div className="flex-grow overflow-y-auto pr-2 -mr-2">
        <ol className="relative border-l border-gray-700 ml-4">
          {sortedEpochs.map((epoch) => (
            <li key={epoch.id} className="mb-10 ml-6">
              <span className={`absolute -left-3 flex items-center justify-center w-6 h-6 rounded-full ring-8 ring-gray-900 ${universe.active_epoch_id === epoch.id ? 'bg-green-500' : 'bg-gray-600'}`}>
                {universe.active_epoch_id === epoch.id ? <CheckCircle size={12} className="text-white" /> : <Clock size={12} className="text-gray-300" />}
              </span>
              <h4 className="flex items-center mb-1 text-lg font-semibold text-white">
                {epoch.name}
                {universe.active_epoch_id === epoch.id && (
                  <span className="bg-green-600 text-green-100 text-sm font-medium mr-2 px-2.5 py-0.5 rounded ml-3">Active</span>
                )}
              </h4>
              {epoch.archetype && <p className="text-sm text-gray-400">Archetype: {epoch.archetype}</p>}
              <p className="text-sm text-gray-500">Created: {new Date(epoch.created_at || '').toLocaleDateString()}</p>
              
              {/* Editing Interface */}
              {editingEpochId === epoch.id ? (
                <div className="mt-4 p-4 bg-gray-900 rounded border border-blue-500 space-y-3">
                  <label className="block text-xs text-blue-300 uppercase font-bold">Narrative Vector (Seed Prose)</label>
                  <textarea 
                    className="w-full h-24 bg-gray-800 text-white p-2 rounded text-sm font-mono"
                    value={editSeedProse}
                    onChange={(e) => setEditSeedProse(e.target.value)}
                    placeholder="Enter the governing narrative for this era..."
                  />
                  
                  <label className="block text-xs text-blue-300 uppercase font-bold">Character Souls (JSON)</label>
                  <textarea 
                    className="w-full h-24 bg-gray-800 text-white p-2 rounded text-sm font-mono"
                    value={editCharacterStances}
                    onChange={(e) => setEditCharacterStances(e.target.value)}
                    placeholder='{"Kaelen": "Skeptical materialist..."}'
                  />
                  
                  <div className="flex gap-2 justify-end">
                    <button onClick={handleCancelEdit} className="px-3 py-1 text-xs text-gray-400 hover:text-white">Cancel</button>
                    <button 
                      onClick={() => handleSaveEpochDetails(epoch.id)}
                      disabled={isLoading}
                      className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-500"
                    >
                      Save Paradigm
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-2">
                   {/* Preview of Details */}
                   {epoch.seed_prose && (
                     <p className="text-xs text-gray-400 italic truncate mb-1">"{epoch.seed_prose.substring(0, 50)}..."</p>
                   )}
                   <div className="flex gap-2">
                    <button 
                        onClick={() => handleStartEdit(epoch)}
                        className="text-xs text-blue-400 hover:underline"
                    >
                        Edit Details
                    </button>
                    {universe.active_epoch_id !== epoch.id && (
                        <button 
                        onClick={() => handleActivateEpoch(epoch.id)}
                        disabled={isLoading}
                        className="text-xs text-green-400 hover:underline disabled:opacity-50"
                        >
                        Activate
                        </button>
                    )}
                   </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-6 pt-4 border-t border-gray-700">
        <button
          onClick={() => setIsCreatingEpoch(!isCreatingEpoch)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 mb-4 bg-blue-600 hover:bg-blue-700 rounded-md text-white font-medium transition-colors"
        >
          <PlusCircle size={16} /> New Paradigm Shift (Epoch)
        </button>

        {isCreatingEpoch && (
          <div className="p-4 bg-gray-700 rounded-md space-y-3">
            <input
              type="text"
              placeholder="New Epoch Name (e.g., The Awakening)"
              value={newEpochName}
              onChange={(e) => setNewEpochName(e.target.value)}
              className="w-full bg-gray-950 border border-gray-600 rounded p-2 text-white"
              disabled={isLoading}
            />
            <select
              value={newEpochArchetype || ''}
              onChange={(e) => setNewEpochArchetype(e.target.value)}
              className="w-full bg-gray-950 border border-gray-600 rounded p-2 text-white disabled:opacity-50"
              disabled={isLoading}
            >
              <option value="" disabled>-- Select Archetype for this Epoch --</option>
              {archetypes.map((arch) => (
                <option key={arch.name.toLowerCase()} value={arch.name.toLowerCase()}>
                  {arch.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleCreateEpoch}
              disabled={isLoading || !newEpochName.trim() || !newEpochArchetype}
              className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-md text-white font-medium transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Creating...' : 'Create & Activate Epoch'}
            </button>
            {feedback && <p className="text-sm text-gray-300 mt-2">{feedback}</p>}
          </div>
        )}
      </div>

      {/* Paradigm Shift Animation/Toast */}
      {showAnimation && (
        <div className="fixed bottom-8 right-8 bg-blue-700 text-white p-4 rounded-lg shadow-xl flex items-center gap-2 animate-bounce-in-out z-50">
          <Sparkles size={20} className="text-yellow-300" />
          <p className="font-medium">{animationMessage}</p>
        </div>
      )}
    </div>
  );
};
