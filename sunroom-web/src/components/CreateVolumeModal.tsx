'use client';

// FIX 1: Added useMemo to imports
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './AuthContext';
import { getApiUrl } from '@/lib/utils';
import axios from 'axios';
import { X, Lightbulb, Sparkles, Loader2, BookCheck, PlusCircle, Globe, Edit, AlertTriangle } from 'lucide-react';
import { 
    Universe as UniverseSchema, 
    Archetype as ArchetypeSchema, 
    Epoch as EpochSchema, 
    getUniverse, 
    getArchetypes, 
    getEpochs,
    createEpoch 
} from '@/services/universeService';

const API_URL = getApiUrl();

// --- Interfaces ---
interface CreateVolumeModalProps {
    onClose: () => void;
}

interface Universe extends UniverseSchema {}
interface Archetype extends ArchetypeSchema {}
interface Epoch extends EpochSchema {}
interface Storyline {
    id: string;
    name: string;
}

export const CreateVolumeModal: React.FC<CreateVolumeModalProps> = ({ onClose }) => {
    // Main State
    const [mode, setMode] = useState<'existing' | 'new'>('existing');
    const [isLoading, setIsLoading] = useState(false);
    const [statusText, setStatusText] = useState('');

    // FIX 2: Added missing state for Epic Mode
    const [isEpicMode, setIsEpicMode] = useState(false);

    // Form State
    const [seedProse, setSeedProse] = useState('');
    const [universes, setUniverses] = useState<Universe[]>([]);
    const [storylines, setStorylines] = useState<Storyline[]>([]);
    const [selectedUniverseId, setSelectedUniverseId] = useState<string | null>(null);
    const [selectedStorylineId, setSelectedStorylineId] = useState<string | null>(null);

    // New Universe State
    const [newUniverseName, setNewUniverseName] = useState('');
    const [newStorylineName, setNewStorylineName] = useState('Volume 1');
    const [newUniverseSeed, setNewUniverseSeed] = useState('');

    // Ontological Preview State
    const [allArchetypes, setAllArchetypes] = useState<Archetype[]>([]);
    const [currentUniverseEpochs, setCurrentUniverseEpochs] = useState<Epoch[]>([]);
    const [currentActiveEpoch, setCurrentActiveEpoch] = useState<Epoch | null>(null);
    const [currentActiveArchetype, setCurrentActiveArchetype] = useState<Archetype | undefined>(undefined);

    // Dependencies
    const router = useRouter(); 
    const { session } = useAuth();

    // --- Data Fetching ---
    const fetchInitialData = useCallback(async () => {
        if (!session) return;
        try {
            const token = session.access_token;
            const [universesResponse, archetypesResponse] = await Promise.all([
                axios.get(`${API_URL}/api/v1/universes`, { headers: { Authorization: `Bearer ${token}` } }),
                getArchetypes()
            ]);
            setUniverses(universesResponse.data);
            setAllArchetypes(archetypesResponse);
            
            if (universesResponse.data.length > 0 && !selectedUniverseId) {
                setSelectedUniverseId(universesResponse.data[0].id);
            }
        } catch (error) {
            console.error("Failed to fetch initial data for modal:", error);
        }
    }, [session, selectedUniverseId]);

    const fetchStorylines = useCallback(async (universeId: string) => {
        if (!session) return;
        try {
            const token = session.access_token;
            const response = await axios.get(`${API_URL}/api/v1/universes/${universeId}/storylines`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setStorylines(response.data);
        } catch (error) {
            console.error("Failed to fetch storylines:", error);
        }
    }, [session]);

    const fetchEpochsForUniverse = useCallback(async (universeId: string) => {
        if (!session) return;
        try {
            const fetchedEpochs = await getEpochs(session.access_token, universeId);
            setCurrentUniverseEpochs(fetchedEpochs);
        } catch (error) {
            console.error(`Failed to fetch epochs for universe ${universeId}:`, error);
        }
    }, [session]);

    useEffect(() => {
        fetchInitialData();
    }, [fetchInitialData]);

    useEffect(() => {
        if (selectedUniverseId) {
            fetchStorylines(selectedUniverseId);
            fetchEpochsForUniverse(selectedUniverseId);
        } else {
            setStorylines([]);
            setCurrentUniverseEpochs([]);
        }
    }, [selectedUniverseId, fetchStorylines, fetchEpochsForUniverse]);

    // Derive current active epoch and archetype
    useEffect(() => {
        const selectedUniverse = universes.find(u => u.id === selectedUniverseId);
        if (selectedUniverse && selectedUniverse.active_epoch_id) {
            const activeEpoch = currentUniverseEpochs.find(e => e.id === selectedUniverse.active_epoch_id);
            setCurrentActiveEpoch(activeEpoch || null);
            if (activeEpoch?.archetype) {
                setCurrentActiveArchetype(allArchetypes.find(a => a.name.toLowerCase() === (activeEpoch.archetype || '').toLowerCase()));
            }
        } else {
            setCurrentActiveEpoch(null);
            setCurrentActiveArchetype(undefined);
        }
    }, [selectedUniverseId, universes, currentUniverseEpochs, allArchetypes]);

    // --- Handlers ---
    const generateVolume = async (universeId: string, storylineId: string, topic: string) => {
        if (!session) return;
        const token = session.access_token;
        const response = await axios.post(`${API_URL}/api/v1/volumes/generate`, {
            topic: topic,
            depth: isEpicMode ? 18 : 6,
            lenses: [], 
            universe_id: universeId,
            storyline_id: storylineId,
            is_epic: isEpicMode,
        }, { headers: { Authorization: `Bearer ${token}` } });
        
        const data = response.data;
        onClose();
        router.push(`/dashboard?highlightVolumeId=${data.volume_id}`);
    };

    const handleCreateAndInitialize = async () => {
        if (!session) return;
        setIsLoading(true);
        setStatusText('Creating new universe...');
        
        try {
            const token = session.access_token;
            const universeResponse = await axios.post(`${API_URL}/api/v1/universes`, 
                { name: newUniverseName, description: newUniverseSeed },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const newUniverse: Universe = universeResponse.data;

            setStatusText('Creating initial epoch...');
            const defaultArchetype = allArchetypes.find(a => a.name.toLowerCase() === 'materialist');
            const initialEpoch = await createEpoch(token, newUniverse.id, {
                name: 'Genesis Epoch',
                archetype: 'materialist',
                system_anchor: defaultArchetype?.system_anchor || "Materialist Laws.",
                prohibitions: defaultArchetype?.prohibitions || [],
            });

            setStatusText('Activating initial epoch...');
            await axios.patch(`${API_URL}/api/v1/universes/${newUniverse.id}`, 
                { active_epoch_id: initialEpoch.id },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            setStatusText('Creating first storyline...');
            const storylineResponse = await axios.post(`${API_URL}/api/v1/storylines`, 
                { universe_id: newUniverse.id, name: newStorylineName },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const newStoryline: Storyline = storylineResponse.data;

            await generateVolume(newUniverse.id, newStoryline.id, seedProse);

        } catch (e) {
            console.error(e);
            alert("Check console for errors.");
            setIsLoading(false);
        }
    };
    
    const handleInitializeExisting = async () => {
        if (!selectedUniverseId || !selectedStorylineId || !session) return;
        setIsLoading(true);
        setStatusText('Initializing new volume...');
        try {
            await generateVolume(selectedUniverseId, selectedStorylineId, seedProse);
        } catch (e) {
            setIsLoading(false);
        }
    };

    const isExistingDisabled = !selectedUniverseId || !selectedStorylineId || !seedProse.trim() || !currentActiveEpoch;
    const isNewDisabled = !newUniverseName.trim() || !newStorylineName.trim() || !seedProse.trim();
    const selectedUniverseObj = universes.find(u => u.id === selectedUniverseId);

    const combinedProhibitions = useMemo(() => {
        if (!currentActiveArchetype) return [];
        return Array.from(new Set([...(currentActiveArchetype.prohibitions || []), ...(currentActiveEpoch?.prohibitions || [])]));
    }, [currentActiveArchetype, currentActiveEpoch]);

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-900 border border-gray-700 p-8 rounded-lg max-w-3xl w-full shadow-2xl relative max-h-[90vh] overflow-y-auto custom-scrollbar">
                <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white"><X size={24} /></button>
                <h2 className="text-2xl font-bold mb-2 text-white">Architect Protocol</h2>
                <p className="text-gray-400 mb-6">Define a universe and a seed for a new volume.</p>

                {/* --- Mode Toggle --- */}
                <div className="flex bg-gray-800 rounded-lg p-1 mb-6">
                    <button onClick={() => setMode('existing')} className={`flex-1 py-2 rounded-md text-sm font-medium transition-all ${mode === 'existing' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-700'}`}>Use Existing Universe</button>
                    <button onClick={() => setMode('new')} className={`flex-1 py-2 rounded-md text-sm font-medium transition-all ${mode === 'new' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:bg-gray-700'}`}>Create New Universe</button>
                </div>

                {mode === 'existing' ? (
                    <div className="grid grid-cols-2 gap-4 mb-6">
                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Select Universe</label>
                            <select onChange={(e) => setSelectedUniverseId(e.target.value || null)} value={selectedUniverseId || ''} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white">
                                <option value="">-- Select --</option>
                                {universes.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Select Storyline</label>
                            <select onChange={(e) => setSelectedStorylineId(e.target.value || null)} value={selectedStorylineId || ''} disabled={!selectedUniverseId} className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white disabled:opacity-50">
                                <option value="">-- Select --</option>
                                {storylines.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                            </select>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4 mb-6">
                        <div className="grid grid-cols-2 gap-4">
                            <input type="text" value={newUniverseName} onChange={e => setNewUniverseName(e.target.value)} className="bg-gray-950 border border-gray-700 rounded p-2 text-white" placeholder="Universe Name" />
                            <input type="text" value={newStorylineName} onChange={e => setNewStorylineName(e.target.value)} className="bg-gray-950 border border-gray-700 rounded p-2 text-white" placeholder="Storyline Name" />
                        </div>
                        <textarea value={newUniverseSeed} onChange={e => setNewUniverseSeed(e.target.value)} className="w-full h-20 bg-gray-950 border border-gray-700 rounded p-2 text-white resize-none" placeholder="Universe concepts/style..."></textarea>
                    </div>
                )}
                
                {/* --- Ontological Preview --- */}
                {selectedUniverseObj && currentActiveEpoch && currentActiveArchetype && (
                    <div className="p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg mb-6">
                        <h3 className="text-sm font-bold text-blue-400 mb-2 flex items-center gap-2"><BookCheck size={16} /> Active Narrative Laws</h3>
                        <p className="text-xs text-gray-300"><strong>Archetype:</strong> {currentActiveArchetype.name} ({currentActiveEpoch.name})</p>
                        <p className="text-[11px] text-gray-400 italic mb-2">{currentActiveArchetype.system_anchor}</p>
                        {combinedProhibitions.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                                {combinedProhibitions.slice(0, 8).map(p => (
                                    <span key={p} className="text-[10px] bg-red-900/30 text-red-400 px-2 py-0.5 rounded border border-red-500/20 line-through">{p}</span>
                                ))}
                                {combinedProhibitions.length > 8 && <span className="text-[10px] text-gray-500">+{combinedProhibitions.length - 8} more</span>}
                            </div>
                        )}
                    </div>
                )}

                {/* --- Mode Toggle & Seed Prose --- */}
                <div className="space-y-6">
                    <div className="flex items-center justify-between bg-gray-800/50 p-3 rounded border border-gray-700">
                        <span className="text-sm font-medium text-gray-300">Production Scale</span>
                        <div className="flex items-center gap-3">
                            <span className={`text-[10px] uppercase font-bold ${!isEpicMode ? 'text-blue-400' : 'text-gray-500'}`}>Draft</span>
                            <button onClick={() => setIsEpicMode(!isEpicMode)} className={`w-10 h-5 rounded-full relative transition-colors ${isEpicMode ? 'bg-purple-600' : 'bg-gray-600'}`}>
                                <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all ${isEpicMode ? 'left-6' : 'left-1'}`} />
                            </button>
                            <span className={`text-[10px] uppercase font-bold ${isEpicMode ? 'text-purple-400' : 'text-gray-500'}`}>Epic</span>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-2"><Edit size={16} className="text-purple-400" /> Volume Seed Prose</label>
                        <textarea value={seedProse} onChange={(e) => setSeedProse(e.target.value)} placeholder="Kaelen surveys the mineral..." className="w-full h-32 bg-gray-950 border border-gray-700 rounded p-4 text-white focus:border-purple-500 focus:outline-none resize-none" />
                    </div>
                </div>

                <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-gray-800">
                    <button onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white">Cancel</button>
                    <button 
                        onClick={mode === 'existing' ? handleInitializeExisting : handleCreateAndInitialize} 
                        disabled={isLoading || (mode === 'existing' ? isExistingDisabled : isNewDisabled)} 
                        className={`px-6 py-2 rounded text-white font-medium shadow-lg transition-all ${isLoading ? 'bg-gray-700 cursor-not-allowed' : (mode === 'existing' ? 'bg-blue-600 hover:bg-blue-500' : 'bg-purple-600 hover:bg-purple-500')}`}
                    >
                        {isLoading ? <span className="flex items-center gap-2"><Loader2 size={16} className="animate-spin" /> {statusText || 'Architecting...'}</span> : 'Initialize Volume'}
                    </button>
                </div>
            </div>
        </div>
    );
};