import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { api } from '../services/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RadarProps {
  volumeId: string;
  onSelectTrailhead: (trailhead: any) => void;
}

export const Radar: React.FC<RadarProps> = ({ volumeId, onSelectTrailhead }) => {
  const [trailheads, setTrailheads] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");

  // 1. Fetch Trailheads (Curator Output)
  const refreshRadar = async () => {
    try {
      setLoading(true);
      // We assume the Curator Agent saves atoms with type='trailhead'
      const res = await api.getTrailheads();
      const nodes = res.data.trailheads || [];
      setTrailheads(nodes);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshRadar();
  }, []);

  // 2. Trigger Manual Scan
  const handleScan = async () => {
    setLoading(true);
    try {
      // Trigger the curator endpoint
      await api.triggerCuratorScan("Science, Philosophy, Mystery, Future History", volumeId);
      // After scan, refresh list
      setTimeout(refreshRadar, 5000); 
    } catch (e) {
      alert("Scan failed");
    } finally {
      setLoading(false);
    }
  };

  // 3. Simple File Upload Handler
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const files = Array.from(e.target.files);
    
    setUploadStatus(`Queueing ${files.length} files...`);
    let successCount = 0;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadStatus(`Ingesting ${i + 1}/${files.length}: ${file.name}...`);
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
          await api.ingestSource(formData);
          successCount++;
        } catch (err) {
          console.error(`Failed to upload ${file.name}`, err);
        }
    }
    
    setUploadStatus(successCount === files.length ? "All files ingested." : `Finished. ${successCount}/${files.length} successful.`);
    setTimeout(() => setUploadStatus(""), 4000);
    e.target.value = ""; // Reset input
  };

  return (
    <div className="h-full flex flex-col p-4 border-r border-slate-800 bg-slate-950">
      <h2 className="text-cyan-400 font-bold uppercase tracking-widest mb-6 text-sm">📡 The Radar</h2>
      
      {/* Ingestion Zone */}
      <div className="mb-4 p-4 border-2 border-dashed border-slate-800 rounded-xl hover:border-slate-600 transition-colors text-center cursor-pointer relative group">
        <input type="file" multiple onChange={handleUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
        <span className="text-2xl block mb-2 group-hover:scale-110 transition-transform">📥</span>
        <span className="text-xs text-slate-500 font-mono group-hover:text-slate-300">Drop Sources Here</span>
      </div>
      
      {uploadStatus && (
          <div className="mb-4 text-[10px] text-cyan-500 font-mono animate-pulse text-center">
              {uploadStatus}
          </div>
      )}

      {/* Controls */}
      <div className="flex justify-between items-center mb-4">
        <span className="text-xs text-slate-400 font-bold">DETECTED SIGNALS</span>
        <button onClick={handleScan} disabled={loading} className="text-xs text-cyan-500 hover:text-cyan-300">
          {loading ? "Scanning..." : "⟳ Scan"}
        </button>
      </div>

      {/* List of Opportunities */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
        {trailheads.length === 0 && <div className="text-xs text-slate-600 italic">No signals detected.</div>}
        
        {trailheads.map((t, i) => (
          <div key={i} onClick={() => onSelectTrailhead(t)} className="bg-slate-900 p-3 rounded border border-slate-800 hover:border-cyan-500 cursor-pointer transition-all group">
            <div className="font-bold text-slate-300 text-sm mb-1 group-hover:text-cyan-400">{t.title}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wide flex justify-between">
                <span>{t.agent_a} + {t.agent_b}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
