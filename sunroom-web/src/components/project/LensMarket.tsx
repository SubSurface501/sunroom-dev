import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

interface LensMarketProps {
  projectId: string;
  currentUser: any;
  onLensesChange: (lenses: string[]) => void;
}

interface ProjectLens {
  id: string;
  name: string; // Cluster label
  user_id: string;
  cluster_id: string;
  owner_email?: string; // We might not have this from atoms, but let's try to display user_id or fetch profile
}

interface ActiveLens {
  cluster_label: string;
  user_id: string;
  mode: string; // 'context' or 'style'
}

export default function LensMarket({ projectId, currentUser, onLensesChange }: LensMarketProps) {
  const [availableLenses, setAvailableLenses] = useState<ProjectLens[]>([]);
  const [activeLenses, setActiveLenses] = useState<ActiveLens[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Academic Mode State
  const [activeTab, setActiveTab] = useState<'project' | 'academic'>('project');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    fetchLensData();
  }, [projectId]);

  const fetchLensData = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      // 1. Get Available Lenses (from all members)
      const resAvailable = await fetch(`${apiUrl}/api/v1/projects/${projectId}/lenses`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
      const availableData = await resAvailable.json();
      setAvailableLenses(availableData);

      // 2. Get Active Lenses (Grant Table)
      const resActive = await fetch(`${apiUrl}/api/v1/projects/${projectId}/lenses/active`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
      const activeData = await resActive.json();
      setActiveLenses(activeData);
      
      // Notify parent of active cluster names
      const activeNames = activeData.map((l: ActiveLens) => l.cluster_label);
      onLensesChange(activeNames);

    } catch (e) {
      console.error("Error fetching lens market:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleAcademicSearch = async () => {
      if (!searchQuery.trim()) return;
      setSearching(true);
      try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
          const { data: { session } } = await supabase.auth.getSession();
          if (!session) return;

          const res = await fetch(`${apiUrl}/api/v1/concepts/search`, {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${session.access_token}`
              },
              body: JSON.stringify({ query: searchQuery, domain: "General Science" })
          });
          
          if (res.ok) {
              const data = await res.json();
              setSearchResults(data.results || []);
          }
      } catch (e) {
          console.error("Search failed:", e);
      } finally {
          setSearching(false);
      }
  };

  const toggleLens = async (lensName: string, userId: string, mode: string = 'context') => {
    const isActive = activeLenses.some(
      al => al.cluster_label === lensName && al.user_id === userId
    );

    // Optimistic Update
    let newActiveLenses;
    if (isActive) {
        newActiveLenses = activeLenses.filter(al => !(al.cluster_label === lensName && al.user_id === userId));
    } else {
        newActiveLenses = [...activeLenses, { cluster_label: lensName, user_id: userId, mode }];
    }
    setActiveLenses(newActiveLenses);
    onLensesChange(newActiveLenses.map(l => l.cluster_label)); 

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      await fetch(`${apiUrl}/api/v1/projects/${projectId}/lenses/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.access_token}` 
        },
        body: JSON.stringify({
            cluster_label: lensName,
            lens_owner_id: userId,
            active: !isActive,
            mode: mode
        })
      });
    } catch (e) {
        console.error("Failed to toggle lens:", e);
        fetchLensData(); // Revert on error
    }
  };

  if (loading) return <div className="text-xs text-gray-500 animate-pulse">Syncing Lens Market...</div>;

  // Group lenses by User
  const lensesByUser: { [userId: string]: ProjectLens[] } = {};
  availableLenses.forEach(lens => {
      if (!lensesByUser[lens.user_id]) lensesByUser[lens.user_id] = [];
      lensesByUser[lens.user_id].push(lens);
  });

  return (
    <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-bold text-yellow-500 flex items-center gap-2">
            <span>⬡</span> The Lens Market
        </h3>
        <div className="flex gap-2 bg-gray-900 rounded p-1">
            <button 
                onClick={() => setActiveTab('project')}
                className={`text-xs px-2 py-1 rounded ${activeTab === 'project' ? 'bg-gray-700 text-white' : 'text-gray-500'}`}
            >
                Project
            </button>
            <button 
                onClick={() => setActiveTab('academic')}
                className={`text-xs px-2 py-1 rounded ${activeTab === 'academic' ? 'bg-purple-900/50 text-purple-200' : 'text-gray-500'}`}
            >
                External
            </button>
        </div>
      </div>
      
      {activeTab === 'project' ? (
        <div className="space-y-4">
            {Object.keys(lensesByUser).map(userId => {
                const isMe = userId === currentUser?.id;
                const userLenses = lensesByUser[userId];
                
                return (
                    <div key={userId} className="flex flex-col gap-1">
                        <div className="text-xs text-gray-400 font-mono uppercase tracking-wider mb-1">
                            {isMe ? "My Lenses" : `Collaborator ${userId.slice(0,4)}...`}
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {userLenses.map(lens => {
                                const isActive = activeLenses.some(al => al.cluster_label === lens.name && al.user_id === lens.user_id);
                                return (
                                    <button
                                        key={`${lens.user_id}-${lens.name}`}
                                        onClick={() => toggleLens(lens.name, lens.user_id)}
                                        className={`
                                            relative px-3 py-1.5 rounded text-xs font-medium transition-all border flex items-center gap-2
                                            ${isActive 
                                                ? 'bg-indigo-900/60 border-indigo-400 text-indigo-100 shadow-[0_0_10px_rgba(99,102,241,0.3)]' 
                                                : 'bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-500 hover:text-gray-300'}
                                        `}
                                    >
                                        {lens.name}
                                        {isActive && (
                                            <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_5px_#4ade80]" />
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                );
            })}
            
            {availableLenses.length === 0 && (
                <div className="text-center py-4 text-gray-500 italic text-xs">
                    No lenses found in this project. Run Auto-Genesis individually to contribute.
                </div>
            )}
        </div>
      ) : (
        <div className="space-y-4">
             <div className="flex gap-2">
                 <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search External Concepts (e.g. Entropy)..."
                    onKeyDown={(e) => e.key === 'Enter' && handleAcademicSearch()}
                    className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white focus:border-purple-500 outline-none"
                 />
                 <button 
                    onClick={handleAcademicSearch}
                    disabled={searching}
                    className="bg-purple-700 hover:bg-purple-600 text-white text-xs px-3 rounded"
                 >
                    {searching ? "..." : "Find"}
                 </button>
             </div>
             
             <div className="space-y-2">
                 {searchResults.map((res, i) => {
                     const isAdded = activeLenses.some(al => al.cluster_label === res.name);
                     return (
                         <div key={i} className="flex items-start justify-between bg-gray-900/50 p-2 rounded border border-purple-900/30">
                             <div>
                                 <div className="text-xs font-bold text-purple-300">{res.name}</div>
                                 <div className="text-[10px] text-gray-500 line-clamp-2">{res.definition}</div>
                             </div>
                             <button
                                onClick={() => toggleLens(res.name, "system", "domain")} // User 'system' for external
                                className={`text-[10px] px-2 py-1 rounded border ${isAdded ? 'bg-green-900 border-green-700 text-green-300' : 'border-purple-700 text-purple-400 hover:bg-purple-900'}`}
                             >
                                {isAdded ? "Active" : "Add"}
                             </button>
                         </div>
                     )
                 })}
             </div>
        </div>
      )}
    </div>
  );
}
