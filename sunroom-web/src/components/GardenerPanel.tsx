'use client';

import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create an axios instance with interceptors (mirroring api.ts logic for auth)
// Or reuse api.ts if we update it. For now, duplication is safer for this isolated component to ensure it works.
const apiClient = axios.create({
  baseURL: API_URL,
});

apiClient.interceptors.request.use((config) => {
  const sbKey = Object.keys(localStorage).find(key => key.startsWith('sb-') && key.endsWith('-auth-token'));
  if (sbKey) {
    const session = JSON.parse(localStorage.getItem(sbKey) || '{}');
    if (session.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  }
  return config;
});

export const GardenerPanel = ({ volumeId }: { volumeId: string }) => {
  const [insights, setInsights] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Poll for insights every 30s
  useEffect(() => {
    const checkGardener = async () => {
      if (!volumeId) return;
      try {
        const res = await apiClient.get(`/api/v1/gardener/insights/${volumeId}`);
        setInsights(res.data.insights || []);
      } catch (e) {
        console.error("Gardener check failed:", e);
      }
    };
    
    checkGardener();
    const interval = setInterval(checkGardener, 30000);
    return () => clearInterval(interval);
  }, [volumeId]);

  const handleBridge = async (insight: any) => {
    setLoading(true);
    try {
      await apiClient.post(`/api/v1/gardener/bridge`, {
        volume_id: volumeId,
        content_a: insight.source_a,
        content_b: insight.source_b
      });
      // Clear that insight
      setInsights(prev => prev.filter(i => i !== insight));
      alert("Bridge created! Check the Graph.");
    } catch (e) {
      console.error(e);
      alert("Failed to bridge.");
    } finally {
      setLoading(false);
    }
  };

  if (insights.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 w-80 bg-slate-900 border border-green-500/50 shadow-2xl rounded-xl p-4 animate-slide-up z-50">
      <div className="flex items-center mb-3">
        <span className="text-xl mr-2">🌿</span>
        <h3 className="text-green-400 font-bold text-sm uppercase tracking-wider">The Gardener</h3>
      </div>
      
      <div className="space-y-3">
        {insights.map((insight, idx) => (
          <div key={idx} className="bg-slate-800 p-3 rounded border border-slate-700 shadow-md">
            <p className="text-xs text-slate-400 mb-2 leading-relaxed">{insight.message}</p>
            <div className="flex items-center justify-between text-xs text-slate-200 mb-3 font-mono">
              <span className="truncate w-24 bg-slate-700/50 px-1 py-0.5 rounded border border-slate-600/50" title={insight.source_a}>{insight.source_a.substring(0,15)}...</span>
              <span className="text-slate-500 mx-1">↔</span>
              <span className="truncate w-24 bg-slate-700/50 px-1 py-0.5 rounded border border-slate-600/50" title={insight.source_b}>{insight.source_b.substring(0,15)}...</span>
            </div>
            <button 
              onClick={() => handleBridge(insight)}
              disabled={loading}
              className="w-full bg-green-900/30 hover:bg-green-800/50 text-green-300 text-xs py-2 rounded transition-colors border border-green-800/50 hover:border-green-600 cursor-pointer font-medium"
            >
              {loading ? "Synthesizing..." : "Generate Bridge Node"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
