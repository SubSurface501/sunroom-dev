'use client';

import React, { useState } from 'react';
import { api } from '../services/api';
import { useRouter } from 'next/navigation';

interface CompositePanelProps {
  volumeId: string;
}

export const CompositePanel: React.FC<CompositePanelProps> = ({ volumeId }) => {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  // In a real app, you'd fetch real users from the DB. 
  // For now, we allow pasting UUIDs or using defaults.
  const [role1, setRole1] = useState('Architect');
  const [user1, setUser1] = useState('57a5073f-6dc5-4b92-ad9b-925d01f8e88d'); // Use valid UUIDs
  const [role2, setRole2] = useState('Biologist');
  const [user2, setUser2] = useState('57a5073f-6dc5-4b92-ad9b-925d01f8e88d'); 
  
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Production State
  const [producing, setProducing] = useState(false);
  const [productionStatus, setProductionStatus] = useState<string>('');
  const [scriptReady, setScriptReady] = useState(false);
  const [reviewResult, setReviewResult] = useState<any | null>(null);

  const handleBraid = async () => {
    setLoading(true);
    const collaboratorMap = {
      [role1]: user1,
      [role2]: user2
    };

    try {
      const res = await api.startCollaboration(prompt, volumeId, collaboratorMap);
      setTranscript(res.data.transcript);
    } catch (e) {
      console.error(e);
      alert("Collaboration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleProduce = async () => {
    if (!prompt) return;
    setProducing(true);
    setScriptReady(false);
    setReviewResult(null);
    setProductionStatus('Initializing Writers Room...');
    
    // Construct a mock trailhead from the current UI state
    const mockTrailhead = {
        title: prompt.slice(0, 50) + "...", // Use the prompt start as title
        premise: prompt,
        agent_a: role1,
        agent_b: role2
    };
    
    try {
      // 1. Start Task
      setProductionStatus('Agents are constructing Project Subgraph (Researching)...');
      
      const startRes = await api.post('/api/v1/production/initialize', {
        trailhead: mockTrailhead,
        volume_id: volumeId
      });
      
      const taskId = startRes.data.task_id;
      
      // 2. Poll for Updates
      const pollInterval = setInterval(async () => {
        try {
            const pollRes = await api.get(`/api/v1/tasks/${taskId}`);
            const { status, result } = pollRes.data;

            if (status === 'SUCCESS') {
                clearInterval(pollInterval);
                setProducing(false);
                setProductionStatus('Complete');
                setScriptReady(true);
                
                if (result.script) {
                    setTranscript(result.script);
                } else {
                     setTranscript("Production complete. Script saved to Atom ID: " + result.script_id);
                }

                if (result.review) {
                  setReviewResult(result.review);
                }

            } else if (status === 'FAILURE') {
                clearInterval(pollInterval);
                setProducing(false);
                setProductionStatus('Error: Production Failed');
                alert("Production Failed: " + result);

            } else if (status === 'PROGRESS') {
                const meta = pollRes.data.result;
                if (meta) {
                    setProductionStatus(`${meta.phase}: ${meta.details}`);
                }
            }
        } catch (pollError) {
            console.error("Polling error", pollError);
        }
      }, 1000);
      
    } catch (e) {
      console.error(e);
      setProductionStatus('Production Failed (Start).');
      alert("Production Failed. Check console.");
      setProducing(false);
    }
  };

  const handleRepurpose = async () => {
    // Trigger the "Volume Architect" to build the interactive graph
    try {
        setLoading(true);
        // We use the same prompt/theme as the script
        const res = await api.post('/api/v1/volumes/generate', {
            theme: prompt,
            root_concept: "Adapted from Script",
            lenses: [role1, role2] 
        });
        
        const taskId = res.data.task_id;
        // Redirect to the Blueprint Editor to watch the graph build
        router.push(`/dashboard/blueprint/${taskId}`);
        
    } catch (e) {
        console.error(e);
        alert("Failed to start Volume generation.");
        setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-slate-900 rounded-xl border border-slate-700 shadow-2xl text-white mt-6 relative">
      <h2 className="text-xl font-bold mb-4 flex items-center">
        <span className="text-cyan-400 mr-2">🎙️</span> The Studio
      </h2>
      
      <p className="text-xs text-slate-400 mb-4">
        Ingest your ideas, generate deep scripts, and crystallize them into interactive volumes.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Collaborator 1 */}
        <div className="p-3 bg-slate-800 rounded border border-slate-600">
          <label className="text-xs text-slate-400">Lens A (Perspective)</label>
          <input value={role1} onChange={e => setRole1(e.target.value)} className="w-full bg-transparent border-b border-slate-600 text-white mb-2 font-bold" />
          {/* Hidden user ID for now to declutter, hardcoded in logic or expanded later if needed */}
        </div>

        {/* Collaborator 2 */}
        <div className="p-3 bg-slate-800 rounded border border-slate-600">
          <label className="text-xs text-slate-400">Lens B (Perspective)</label>
          <input value={role2} onChange={e => setRole2(e.target.value)} className="w-full bg-transparent border-b border-slate-600 text-white mb-2 font-bold" />
        </div>
      </div>

      <div className="mb-4">
        <label className="text-xs text-cyan-400 font-bold uppercase tracking-wider mb-2 block">
            The Seed / Draft (1-Page Input)
        </label>
        <textarea 
            className="w-full bg-slate-800 border border-slate-600 rounded p-4 text-slate-200 focus:ring-2 focus:ring-cyan-500 outline-none text-sm leading-relaxed"
            rows={8}
            placeholder="Paste your rough draft, notes, or core idea here. The Agents will research and expand this into a full script."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
        />
      </div>

      <div className="flex gap-3">
          <button 
            onClick={handleBraid}
            disabled={loading || producing}
            className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium py-3 px-4 rounded flex justify-center items-center transition-all cursor-pointer disabled:opacity-50 text-sm"
          >
            {loading ? "Thinking..." : "Quick Context Check"}
          </button>
          
          <button 
            onClick={handleProduce}
            disabled={loading || producing}
            className="flex-[2] bg-gradient-to-r from-cyan-700 to-blue-700 hover:from-cyan-600 hover:to-blue-600 text-white font-bold py-3 px-4 rounded flex justify-center items-center transition-all cursor-pointer disabled:opacity-50 shadow-lg border border-cyan-500/30"
          >
            {producing ? "Producing..." : "🎬 Produce Video Script"}
          </button>
      </div>

      {transcript && (
        <div className="mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-cyan-400 text-sm font-bold uppercase">Generated Script</h3>
                
                {scriptReady && (
                    <div className="flex gap-2">
                        <button 
                            onClick={handleRepurpose}
                            className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold py-2 px-4 rounded-full flex items-center gap-2 transition-all shadow-lg shadow-purple-500/20"
                        >
                            <span>🔮</span>
                            Repurpose into Picture Book
                        </button>
                    </div>
                )}
            </div>

            {/* NEW: Ontological Status Box */}
            {reviewResult && (
              <div className="mb-4 p-4 bg-slate-950 border border-slate-700 rounded-lg flex flex-col gap-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Ontological Status</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400 font-mono">Fidelity:</span>
                    <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-1000 ${reviewResult.score > 0.8 ? 'bg-emerald-500' : 'bg-yellow-500'}`} 
                        style={{ width: `${reviewResult.score * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {reviewResult.character_audit && Object.entries(reviewResult.character_audit).map(([char, status]: [string, any]) => (
                    <div key={char} className="flex items-center gap-2 p-2 bg-slate-900/50 rounded border border-slate-800/50">
                      <span className={status.toLowerCase().includes('pass') ? 'text-emerald-400' : 'text-red-400'}>
                        {status.toLowerCase().includes('pass') ? '✓' : '⚠'}
                      </span>
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-slate-300 leading-none">{char}</span>
                        <span className="text-[8px] text-slate-500 truncate max-w-[100px]">{status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="p-6 bg-slate-800 rounded-lg border-l-4 border-cyan-500 max-h-[500px] overflow-y-auto shadow-inner">
                <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap font-serif">{transcript}</p>
            </div>
        </div>
      )}
      
      {/* Production Status Modal */}
      {producing && (
        <div className="absolute inset-0 bg-slate-900/95 backdrop-blur-md flex items-center justify-center z-50 rounded-xl border border-cyan-500/30">
          <div className="p-6 w-full text-center">
            <div className="flex justify-center mb-6 relative">
               <div className="w-16 h-16 border-4 border-slate-700 rounded-full absolute"></div>
               <div className="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin relative z-10"></div>
            </div>
            <h3 className="text-2xl font-bold text-white mb-2 tracking-tight">Writers' Room Active</h3>
            <p className="text-cyan-400 font-mono text-sm mb-8">{productionStatus}</p>
            
            <div className="space-y-3 text-xs text-slate-500 font-mono text-left max-w-xs mx-auto border-l border-slate-700 pl-4">
              <div className={`transition-all duration-300 ${productionStatus.includes('Research') ? 'text-cyan-300 font-bold translate-x-1' : ''}`}>
                [1] Phase 1: Subgraph Expansion
              </div>
              <div className={`transition-all duration-300 ${productionStatus.includes('Structure') || productionStatus.includes('Architect') ? 'text-cyan-300 font-bold translate-x-1' : ''}`}>
                [2] Phase 2: Narrative Structuring
              </div>
              <div className={`transition-all duration-300 ${productionStatus.includes('Drafting') || productionStatus.includes('Finalizing') ? 'text-cyan-300 font-bold translate-x-1' : ''}`}>
                [3] Phase 3: Script Synthesis
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
