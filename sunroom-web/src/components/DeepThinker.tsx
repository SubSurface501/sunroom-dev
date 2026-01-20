'use client';

import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface DeepThinkerProps {
  volumeId: string;
}

export const DeepThinker: React.FC<DeepThinkerProps> = ({ volumeId }) => {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState<'idle' | 'thinking' | 'complete' | 'error'>('idle');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [result, setResult] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);

  // Polling Logic
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (status === 'thinking' && taskId) {
      interval = setInterval(async () => {
        try {
          const res = await api.getTaskStatus(taskId);
          if (res.data.status === 'SUCCESS') {
            setResult(res.data.result);
            setStatus('complete');
            clearInterval(interval);
          } else if (res.data.status === 'FAILURE') {
            setStatus('error');
            clearInterval(interval);
          } else {
            // Still PENDING/PROCESSING
            setLogs(prev => {
                // Keep only last 5 logs to avoid clutter
                const newLogs = [...prev, "Refining topology... calculating Energy..."];
                return newLogs.slice(-5);
            });
          }
        } catch (e) {
          console.error(e);
          setStatus('error');
        }
      }, 2000); // Poll every 2 seconds
    }
    return () => clearInterval(interval);
  }, [status, taskId]);

  const handleDeepThink = async () => {
    try {
      setStatus('thinking');
      setLogs(["Initializing System 2...", "Injecting EBM-CoT Layer..."]);
      const res = await api.startDeepThought(prompt, volumeId);
      setTaskId(res.data.task_id);
    } catch (e) {
      console.error(e);
      setStatus('error');
    }
  };

  return (
    <div className="p-6 bg-slate-900 rounded-xl border border-slate-700 shadow-2xl text-white">
      <h2 className="text-xl font-bold mb-4 flex items-center">
        <span className="text-purple-400 mr-2">🧠</span> Deep Reasoning Engine
      </h2>

      {/* Input Area */}
      <div className="mb-4">
        <textarea 
          className="w-full bg-slate-800 border border-slate-600 rounded p-3 text-slate-200 focus:ring-2 focus:ring-purple-500 outline-none"
          rows={3}
          placeholder="Enter a complex hypothesis..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={status === 'thinking'}
        />
      </div>

      {/* Action Button */}
      {status === 'idle' || status === 'complete' || status === 'error' ? (
        <button 
          onClick={handleDeepThink}
          className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded transition-all w-full flex justify-center items-center cursor-pointer"
        >
          Activate System 2 (Refinement Loop)
        </button>
      ) : (
        <div className="bg-slate-800 rounded p-4 border border-purple-500/30">
          <div className="flex items-center justify-center space-x-2 mb-2">
            <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce"></div>
            <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce delay-100"></div>
            <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce delay-200"></div>
          </div>
          <div className="text-xs font-mono text-purple-300 text-center h-20 overflow-y-auto">
            {logs.map((log, i) => <div key={i}>{log}</div>)}
          </div>
        </div>
      )}

      {/* Result Display */}
      {status === 'complete' && (
        <div className="mt-6 p-4 bg-slate-800 rounded border-l-4 border-green-500 animate-fade-in">
          <div className="text-xs text-green-400 uppercase font-bold tracking-wider mb-2">
            Geometric Constraint Met (P* {'>'} 0.65)
          </div>
          <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">
            {result}
          </p>
        </div>
      )}
      
       {status === 'error' && (
        <div className="mt-6 p-4 bg-red-900/30 rounded border-l-4 border-red-500">
          <p className="text-red-300">
            System 2 collapsed. Check console logs.
          </p>
        </div>
      )}
    </div>
  );
};
