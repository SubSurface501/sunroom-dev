'use client';

import React, { useEffect, useState } from 'react';
import { GraphView } from '../../../components/GraphView'; 
import { NodeDetailsPanel } from '../../../components/graph/NodeDetailsPanel'; 
import { useStoryStore } from '../../../stores/storyStore';
import axios from 'axios';
import { getApiUrl } from '@/lib/utils';
import { useAuth } from '@/components/AuthContext';

const API_URL = getApiUrl();

export default function StudioPage({ params }: { params: { volumeId: string } }) {
  const volumeId = params.volumeId;
  
  const { setVolume } = useStoryStore();
  const { user, session } = useAuth();
  
  // NEW: State for the Time Machine
  const [activeEpoch, setActiveEpoch] = useState<number>(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (volumeId && user && session) {
        const initStudio = async () => {
             try {
                const token = session.access_token;
                const headers = { Authorization: `Bearer ${token}` };

                // 1. Fetch Volume
                const volRes = await axios.get(`${API_URL}/api/v1/volumes/${volumeId}`, { headers });
                const volumeData = volRes.data;
                setVolume(volumeData);

                // 2. Fetch Universe to get "Time" (Active Epoch)
                if (volumeData.universe_id) {
                    const uniRes = await axios.get(`${API_URL}/api/v1/universes/${volumeData.universe_id}`, { headers });
                    if (uniRes.data && uniRes.data.active_epoch_id) {
                        setActiveEpoch(uniRes.data.active_epoch_id);
                    }
                }
             } catch(e) {
                 console.error("Failed to load studio context", e);
             } finally {
                 setLoading(false);
             }
        }
        initStudio();
    }
  }, [volumeId, user, session, setVolume]);

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      {/* The Canvas (System 2 Creation) */}
      <div className="flex-1 bg-gray-950 relative h-full">
        {!loading && (
            // FIXED: Passing the required currentEpoch prop
            <GraphView volumeId={volumeId} currentEpoch={activeEpoch} />
        )}
        
        <div className="absolute top-4 right-4 bg-gray-900/80 p-2 rounded text-xs text-gray-400 z-10 border border-gray-700">
          <span className="text-purple-400 font-bold">●</span> Epoch {activeEpoch} Active
        </div>
      </div>

      {/* The Controls (Detail & Expansion) */}
      <div className="w-96 border-l border-gray-800 bg-gray-900 h-full overflow-hidden flex flex-col">
        <NodeDetailsPanel />
      </div>
    </div>
  );
};