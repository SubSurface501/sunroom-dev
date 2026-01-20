'use client';
import { useState, useEffect } from 'react';
import { Send, Sparkles, Loader2, Book } from 'lucide-react';
import { api } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import VolumeReader from './VolumeReader';

interface SunRoomProps {
  projectId: string;
}

export default function SunRoom({ projectId }: SunRoomProps) {
  const [prompt, setPrompt] = useState('');
  const [lens, setLens] = useState('The Academic'); // Default lens
  const [isGenerating, setIsGenerating] = useState(false);
  const [volumes, setVolumes] = useState<any[]>([]);
  const [readingVolume, setReadingVolume] = useState<any | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // Get Auth Token
  useEffect(() => {
      supabase.auth.getSession().then(({ data: { session } }) => {
          if (session) setToken(session.access_token);
      });
  }, []);

  // Poll for volumes
  const fetchVolumes = async () => {
    if (!token || !projectId) return;
    try {
      const data = await api.getVolumes(token, projectId); 
      setVolumes(data || []);
    } catch (e) {
      console.error("Failed to load volumes", e);
    }
  };

  useEffect(() => {
    fetchVolumes();
    const interval = setInterval(fetchVolumes, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, [projectId, token]);

  const handleGenerate = async () => {
    if (!prompt.trim() || !token) return;
    setIsGenerating(true);
    
    try {
      await api.triggerSynthesis(token, projectId, prompt, lens);
      setPrompt('');
    } catch (e) {
      alert("Failed to start Director.");
    } finally {
      setTimeout(() => setIsGenerating(false), 2000);
    }
  };

  const openReader = async (vol: any) => {
      if (vol.status !== 'completed' || !token) return;
      try {
          // Fetch full content if not already present
          if (!vol.manuscript) {
             const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/synthesis/volumes/${vol.id}/content`, {
                 headers: { 'Authorization': `Bearer ${token}` }
             });
             const data = await res.json();
             vol.content = data.content; 
          }
          setReadingVolume(vol);
      } catch(e) {
          console.error("Failed to open volume", e);
      }
  }

  return (
    <div className="flex flex-col h-full bg-white/50 backdrop-blur-md rounded-xl border border-white/20 shadow-xl overflow-hidden text-gray-900">
      
      {/* 1. The Output Stream (History) */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {volumes.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>The Room is quiet. Ask the Director to synthesize a volume.</p>
          </div>
        )}

        {volumes.map((vol) => (
          <div 
            key={vol.id} 
            onClick={() => openReader(vol)}
            className={`p-4 rounded-lg border transition-all cursor-pointer group
              ${vol.status === 'completed' 
                ? 'bg-white border-gray-200 hover:border-indigo-300 hover:shadow-md' 
                : 'bg-indigo-50 border-indigo-100 animate-pulse'}`}
          >
            <div className="flex justify-between items-start">
              <div className="flex gap-3">
                <div className={`p-2 rounded-lg ${vol.status === 'completed' ? 'bg-indigo-100 text-indigo-600' : 'bg-indigo-200 text-indigo-700'}`}>
                  {vol.status === 'completed' ? <Book className="w-5 h-5" /> : <Loader2 className="w-5 h-5 animate-spin" />}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">
                    {vol.title || "Untitled Volume"}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {vol.status === 'completed' ? `Ready to read • Created today` : 'The Director is working...'}
                  </p>
                </div>
              </div>
              {vol.status === 'completed' && (
                <span className="text-xs font-medium px-2 py-1 bg-gray-100 text-gray-600 rounded">
                  Read Now
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 2. The Input Console */}
      <div className="p-4 border-t bg-white/80">
        <div className="flex gap-2 mb-2 overflow-x-auto pb-2">
          {['The Academic', 'The Skeptic', 'The Visionary', 'The Journalist'].map((l) => (
            <button
              key={l}
              onClick={() => setLens(l)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors whitespace-nowrap
                ${lens === l ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
            >
              {l}
            </button>
          ))}
        </div>
        
        <div className="relative">
          <textarea 
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the volume you want to create (e.g., 'Analyze the symbolism in the uploaded videos...')"
            className="w-full pl-4 pr-12 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none h-24 bg-white shadow-inner text-gray-900"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleGenerate();
              }
            }}
          />
          <button 
            onClick={handleGenerate}
            disabled={isGenerating || !prompt.trim()}
            className="absolute right-3 bottom-3 p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isGenerating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* 3. The Reader Modal */}
      {readingVolume && (
        <VolumeReader 
          content={readingVolume.content || "# Loading..."} 
          title={readingVolume.title}
          onClose={() => setReadingVolume(null)}
        />
      )}
    </div>
  );
}
