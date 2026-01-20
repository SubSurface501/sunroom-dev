import React, { useEffect, useState } from 'react';

// Types (based on Atom schema)
interface GapAtom {
  id: string;
  name: string;
  type: string;
  content: string; // The "Definition" or context of the gap
  created_at: string;
  metadata?: {
    source_id?: string;
    definition?: string;
  };
}

interface GapMapProps {
  apiBaseUrl?: string;
  token?: string;
}

export default function GapMap({ apiBaseUrl = 'http://localhost:8000', token }: GapMapProps) {
  const [gaps, setGaps] = useState<GapAtom[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGaps();
  }, [token]);

  const fetchGaps = async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      const res = await fetch(`${apiBaseUrl}/api/v1/knowledge/gaps`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!res.ok) throw new Error('Failed to fetch knowledge gaps');
      
      const data = await res.json();
      setGaps(data.gaps || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthorizeDiscovery = (gapId: string) => {
    // Placeholder for Phase 2 integration
    alert(`Authorized discovery for Gap ID: ${gapId}. Estimated cost: $0.05`);
  };

  if (loading) return <div className="p-4 text-white animate-pulse">Scanning the Knowledge Frontier...</div>;
  if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

  return (
    <div className="w-full h-full p-6 bg-slate-900 text-slate-100 overflow-y-auto">
      <div className="mb-8 border-b border-slate-700 pb-4">
        <h2 className="text-2xl font-light tracking-widest text-cyan-400 uppercase">Knowledge Frontier</h2>
        <p className="text-sm text-slate-400 mt-2">
          Detected {gaps.length} gaps in the current world model.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {gaps.length === 0 ? (
            <div className="col-span-full text-center text-slate-500 py-12 italic">
                The map is complete. No known unknowns.
            </div>
        ) : (
            gaps.map((gap) => (
            <div 
                key={gap.id} 
                className="relative group bg-slate-800 border border-slate-700 hover:border-cyan-500/50 rounded-lg p-5 transition-all duration-300 hover:shadow-[0_0_15px_rgba(6,182,212,0.15)]"
            >
                {/* Pulsing "Open" Indicator */}
                <div className="absolute top-4 right-4 flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500"></span>
                </span>
                <span className="text-xs text-orange-400 font-mono uppercase tracking-wider">Open Loop</span>
                </div>

                <h3 className="text-lg font-medium text-slate-200 mb-2 pr-8">{gap.name}</h3>
                
                <div className="text-sm text-slate-400 mb-4 line-clamp-3 font-serif italic">
                "{gap.content || gap.metadata?.definition || 'No context available.'}"
                </div>

                <div className="mt-4 pt-4 border-t border-slate-700/50 flex justify-between items-center">
                <span className="text-xs text-slate-500 font-mono">
                    SRC: {gap.metadata?.source_id ? gap.metadata.source_id.slice(0, 8) : 'UNK'}...
                </span>
                
                <button 
                    onClick={() => handleAuthorizeDiscovery(gap.id)}
                    className="px-3 py-1.5 bg-cyan-900/30 hover:bg-cyan-900/50 text-cyan-300 text-xs font-mono uppercase tracking-wider border border-cyan-800 rounded transition-colors"
                >
                    Authorize Search ($0.05)
                </button>
                </div>
            </div>
            ))
        )}
      </div>
    </div>
  );
}
