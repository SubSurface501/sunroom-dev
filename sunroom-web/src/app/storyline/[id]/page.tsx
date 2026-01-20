'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { getApiUrl } from '@/lib/utils';
import { useAuth } from '@/components/AuthContext';
import { ArrowLeft, BookOpen, CheckCircle, Clock, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import Link from 'next/link';

const API_URL = getApiUrl();

interface Volume {
  id: string;
  title: string;
  status: string;
  created_at: string;
  manuscript?: any;
  universe_id: string;
  epoch_id: number; // Add epoch_id to Volume interface
}

interface Storyline {
  id: string;
  name: string;
  summary: string;
  universe_name: string;
  universe_id: string; // Add universe_id to Storyline interface
  volumes: Volume[];
}

interface Universe {
  id: string;
  name: string;
  active_epoch_id: number;
}

interface Epoch {
  id: number;
  name: string;
  seed_prose: string;
}

export default function StorylinePage({ params }: { params: { id: string } }) {
  const { user, session } = useAuth();
  const router = useRouter();
  const [storyline, setStoryline] = useState<Storyline | null>(null);
  const [universe, setUniverse] = useState<Universe | null>(null);
  const [epochs, setEpochs] = useState<Epoch[]>([]); // New state for Epochs
  const [loading, setLoading] = useState(true);
  const [illustrating, setIllustrating] = useState(false);
  const [advancingEpoch, setAdvancingEpoch] = useState<string | null>(null); // Use volume ID for loading state
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [seedProse, setSeedProse] = useState('');
  const [draftingBlueprint, setDraftingBlueprint] = useState(false);

  const fetchEpochs = async (universeId: string) => {
    if (!session || !universeId) return;
    try {
      const token = session.access_token;
      const res = await axios.get(`${API_URL}/api/v1/universes/${universeId}/epochs`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEpochs(res.data);
    } catch (e) {
      console.error("Failed to load epochs", e);
    }
  };

  const fetchUniverse = async (universeId: string) => {
    if (!session || !universeId) return;
    try {
      const token = session.access_token;
      const res = await axios.get(`${API_URL}/api/v1/universes/${universeId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUniverse(res.data);
      fetchEpochs(universeId); // Fetch epochs after getting universe
    } catch (e) {
      console.error("Failed to load universe", e);
    }
  };

  const fetchStoryline = async () => {
    if (!session) return;
    try {
        const token = session.access_token;
        const res = await axios.get(`${API_URL}/api/v1/storylines/${params.id}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        setStoryline(res.data);
        if (res.data?.universe_id && res.data.universe_id !== universe?.id) {
          fetchUniverse(res.data.universe_id);
        }
    } catch (e) {
        console.error("Failed to load storyline", e);
    } finally {
        setLoading(false);
    }
  };

  useEffect(() => {
    fetchStoryline();
    const interval = setInterval(fetchStoryline, 3000);
    return () => clearInterval(interval);
  }, [session, params.id]);

  const handleIllustrateSaga = async () => {
    if (!storyline || !session) return;
    const lastVolume = storyline.volumes[storyline.volumes.length - 1];
    if (!lastVolume) return;

    setIllustrating(true);
    try {
        const token = session.access_token;
        await axios.post(`${API_URL}/api/v1/volumes/${lastVolume.id}/illustrate`, {}, {
            headers: { Authorization: `Bearer ${token}` }
        });
        alert("Grand Unification Started: The Saga is being illustrated!");
    } catch (e) {
        console.error(e);
        alert("Failed to start illustration.");
    } finally {
        setTimeout(() => setIllustrating(false), 2000);
    }
  };

  const handleFinalizeAndAdvance = async (volumeId: string) => {
    if (!session) return;
    setAdvancingEpoch(volumeId);
    try {
      const token = session.access_token;
      await axios.post(`${API_URL}/api/v1/volumes/${volumeId}/advance_epoch`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Polling will handle UI updates
    } catch (e) {
      console.error(e);
      alert("Failed to finalize and advance epoch.");
    } finally {
      setAdvancingEpoch(null);
    }
  };
  
  const handleOpenDraftModal = () => {
    if (!universe || !epochs) return;
    // The universe's active_epoch_id has already been advanced.
    // We need to find the seed prose for this *new* active epoch.
    const nextEpochData = epochs.find(e => e.id === universe.active_epoch_id);
    if (nextEpochData && nextEpochData.seed_prose) {
      setSeedProse(nextEpochData.seed_prose);
    } else {
      setSeedProse(''); // Clear if no prose is found, allowing manual entry
    }
    setShowDraftModal(true);
  };

  const handleDraftNextEpoch = async () => {
    if (!storyline || !universe || !session || !seedProse.trim()) return;
    setDraftingBlueprint(true);

    try {
      const token = session.access_token;
      const payload = {
        topic: `Epoch ${universe.active_epoch_id}: ${storyline.name}`,
        seed_prose: seedProse,
        universe_id: storyline.universe_id,
        storyline_id: storyline.id,
      };

      const response = await axios.post(`${API_URL}/api/v1/volumes/generate`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // VITAL FIX: Navigate to the blueprint page immediately
      if (response.data && response.data.task_id) {
        router.push(`/dashboard/blueprint/${response.data.task_id}`);
      } else {
        // Fallback in case task_id is not returned
        alert(`Drafting blueprint for Epoch ${universe.active_epoch_id} started!`);
        setShowDraftModal(false);
      }
      
      setSeedProse('');
    } catch (e) {
      console.error(e);
      alert("Failed to draft next epoch blueprint.");
    } finally {
      setDraftingBlueprint(false);
    }
  };

  const allTextReady = useMemo(() => {
      if (!storyline || storyline.volumes.length === 0) return false;
      return storyline.volumes.every(v => ['text_ready', 'published', 'completed', 'illustrating'].includes(v.status));
  }, [storyline]);

  const canAdvanceEpoch = useMemo(() => {
    if (!storyline || !universe || storyline.volumes.length === 0) return false;
    const lastVolume = storyline.volumes[storyline.volumes.length - 1];
    const isLastVolumeComplete = ['text_ready', 'completed', 'published'].includes(lastVolume.status);
    const isCurrentEpoch = lastVolume.epoch_id === universe.active_epoch_id;
    return isLastVolumeComplete && isCurrentEpoch;
  }, [storyline, universe]);

  const canDraftNextEpoch = useMemo(() => {
    if (!storyline || !universe || epochs.length === 0) return false;
    // True if there are no volumes OR if the universe's active epoch is greater than the last volume's epoch
    const lastVolumeEpochId = storyline.volumes.length > 0 ? storyline.volumes[storyline.volumes.length - 1].epoch_id : 0;
    return universe.active_epoch_id > lastVolumeEpochId;
  }, [storyline, universe, epochs]);

  const epochInfo = useMemo(() => {
    if (!universe || !epochs || epochs.length === 0) {
      return { current: '...', total: '...' };
    }
    
    const total = epochs.length;
    // The epochs array is sorted by ID from the DB, which represents their creation order.
    const currentIndex = epochs.findIndex(e => e.id === universe.active_epoch_id);
    const current = currentIndex !== -1 ? currentIndex + 1 : universe.active_epoch_id; // Fallback to ID if not found
    
    return { current, total };
  }, [universe, epochs]);
  
  if (loading) return <div className="h-screen bg-gray-950 flex items-center justify-center text-purple-500"><Loader2 className="animate-spin" /></div>;
  if (!storyline) return <div className="h-screen bg-gray-950 flex items-center justify-center text-gray-500">Saga not found.</div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white font-sans p-8">
      
      <div className="max-w-5xl mx-auto mb-10">
        <Link href="/dashboard" className="text-gray-500 hover:text-white flex items-center gap-2 mb-4 transition-colors">
            <ArrowLeft size={16} /> Back to Radar
        </Link>
        <div className="flex justify-between items-end">
            <div>
                <h2 className="text-purple-400 font-bold uppercase tracking-widest text-sm mb-2">{storyline.universe_name}</h2>
                <h1 className="text-4xl font-bold font-serif">{storyline.name}</h1>
            </div>
            
            <div className="flex items-center gap-4">
              <button 
                  onClick={handleIllustrateSaga}
                  disabled={!allTextReady || illustrating}
                  className={`px-6 py-3 rounded-lg font-bold flex items-center gap-2 shadow-xl transition-all ${allTextReady ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white' : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'}`}
              >
                  {illustrating ? <Loader2 className="animate-spin" /> : <Sparkles />}
                  {allTextReady ? "Compile & Illustrate Saga" : "Waiting for Epochs..."}
              </button>

              {canDraftNextEpoch && (
                <button
                  onClick={handleOpenDraftModal}
                  className="px-6 py-3 rounded-lg font-bold flex items-center gap-2 shadow-xl transition-all bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-500 hover:to-teal-500 text-white"
                >
                  <BookOpen size={16} />
                  Draft Epoch {epochInfo.current} of {epochInfo.total} Blueprint
                </button>
              )}
            </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto space-y-6 relative">
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-800 -z-10"></div>

        {storyline.volumes.map((vol, index) => {
            const isLastVolume = index === storyline.volumes.length - 1;
            const displayEpochNum = epochs.findIndex(e => e.id === vol.epoch_id);
            const displayEpochNum_Actual = displayEpochNum !== -1 ? displayEpochNum + 1 : index + 1;

            return (
            <div key={vol.id} className="relative pl-20">
                <div className={`absolute left-[26px] top-6 w-4 h-4 rounded-full border-2 z-10 transition-colors ${['completed', 'published'].includes(vol.status) ? 'bg-emerald-500 border-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : vol.status === 'text_ready' ? 'bg-blue-500 border-blue-500' : ['drafting', 'writing', 'architecting'].includes(vol.status) ? 'bg-yellow-500 border-yellow-500 animate-pulse' : 'bg-gray-950 border-gray-600'}`}></div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-purple-500/50 transition-all group">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <span className="text-xs font-mono text-gray-500 mb-1 block">EPOCH {displayEpochNum_Actual}</span>
                            <h3 className="text-xl font-bold text-gray-100">{vol.title}</h3>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-xs uppercase font-bold tracking-wider px-2 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700">
                                {vol.status.replace('_', ' ')}
                            </span>
                            {isLastVolume && canAdvanceEpoch && (
                                <button
                                    onClick={() => handleFinalizeAndAdvance(vol.id)}
                                    disabled={advancingEpoch === vol.id}
                                    className={`
                                        px-4 py-2 rounded-lg font-bold flex items-center gap-2 text-sm shadow-md transition-all
                                        ${advancingEpoch === vol.id
                                            ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                                            : 'bg-indigo-600 hover:bg-indigo-500 text-white'}
                                    `}
                                >
                                    {advancingEpoch === vol.id ? <Loader2 className="animate-spin" size={16} /> : <CheckCircle size={16} />}
                                    Finalize & Advance to Epoch {displayEpochNum_Actual + 1}
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="flex gap-3">
                        {['architecting', 'drafting'].includes(vol.status) ? (
                             <Link href={`/dashboard/blueprint/${vol.id}`} className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded text-sm font-medium">
                                Review Blueprint
                             </Link>
                        ) : (
                             <Link href={`/volume/${vol.id}/map`} className="bg-slate-800 hover:bg-slate-700 text-gray-300 px-4 py-2 rounded text-sm font-medium">
                                Inspect Graph
                             </Link>
                        )}
                        
                        {['completed', 'text_ready', 'published'].includes(vol.status) && (
                             <Link href={`/play/${vol.id}`} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded text-sm font-medium flex items-center gap-2">
                                <BookOpen size={16} /> Read Manuscript
                             </Link>
                        )}
                    </div>
                </div>
            </div>
        )})}

        {storyline.volumes.length === 0 && (
            <div className="text-center py-20 text-gray-500 italic">
                The Saga has just begun. Initialize the first volume to start the timeline.
            </div>
        )}
      </div>

      {showDraftModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-8 w-full max-w-2xl shadow-xl">
            <h3 className="text-2xl font-bold mb-4 text-white">Draft Blueprint for Epoch {epochInfo.current} of {epochInfo.total}</h3>
            <p className="text-gray-400 mb-6">Review and edit the seed prose below to guide the Architect.</p>
            <textarea
              className="w-full p-3 h-40 bg-gray-800 text-white rounded-md border border-gray-700 focus:ring-purple-500 focus:border-purple-500 outline-none resize-none font-mono"
              value={seedProse}
              onChange={(e) => setSeedProse(e.target.value)}
              placeholder="The story continues..."
            />
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowDraftModal(false)} className="px-5 py-2 rounded-lg text-gray-300 bg-gray-700 hover:bg-gray-600 transition-colors font-medium">
                Cancel
              </button>
              <button
                onClick={handleDraftNextEpoch}
                disabled={draftingBlueprint || !seedProse.trim()}
                className={`
                    px-5 py-2 rounded-lg font-bold flex items-center gap-2 transition-all
                    ${draftingBlueprint || !seedProse.trim()
                        ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                        : 'bg-green-600 hover:bg-green-500 text-white'}
                `}
              >
                {draftingBlueprint ? <Loader2 className="animate-spin" size={16} /> : <Sparkles size={16} />}
                Draft Blueprint
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}