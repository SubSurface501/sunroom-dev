import React, { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

interface PersonaProfile {
  core_concepts: { name: string; weight: number }[];
  stylistic_attributes: { tone: string; reasoning_pattern: string; vocabulary_complexity: string; keywords: string[] };
  last_updated: string;
}

export default function PersonaEditor() {
  const [profile, setProfile] = useState<PersonaProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) return;

        // Ideally we fetch via API, but for MVP direct Supabase select if RLS allows
        const { data, error } = await supabase
            .from('persona_profiles')
            .select('core_concepts, stylistic_attributes, last_updated')
            .eq('user_id', user.id)
            .single();
        
        if (data) setProfile(data as any); // Cast for now
    } catch (e) {
        console.error(e);
    } finally {
        setLoading(false);
    }
  };

  const handleUpdateStyle = async (field: string, value: string) => {
      if (!profile) return;
      const newStyle = { ...profile.stylistic_attributes, [field]: value };
      
      // Optimistic update
      setProfile({ ...profile, stylistic_attributes: newStyle });
      
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      await supabase
        .from('persona_profiles')
        .update({ stylistic_attributes: newStyle })
        .eq('user_id', user.id);
  };

  if (loading) return <div className="p-6 text-gray-400">Loading Persona...</div>;
  if (!profile) return <div className="p-6 text-gray-400">No Persona Profile found. Wait for the Cartographer to run.</div>;

  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
        <h2 className="text-xl font-light text-yellow-500 mb-6 flex items-center gap-2">
            <span>🪞</span> The Mirror (Persona Editor)
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Core Concepts */}
            <div>
                <h3 className="text-sm font-bold text-gray-500 uppercase mb-4 tracking-widest">Core Concepts (The Pillars)</h3>
                <div className="flex flex-wrap gap-2">
                    {profile.core_concepts?.map((c, i) => (
                        <div key={i} className="px-3 py-1 bg-gray-900 border border-gray-700 rounded-full text-sm text-gray-300 flex items-center gap-2">
                            {c.name}
                            <span className="text-xs text-gray-600">{(c.weight * 10).toFixed(0)}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Stylistic Attributes */}
            <div className="space-y-6">
                <h3 className="text-sm font-bold text-gray-500 uppercase mb-4 tracking-widest">Stylistic Voice</h3>
                
                <div>
                    <label className="text-xs text-gray-400 mb-1 block">Tone</label>
                    <input 
                        type="text" 
                        value={profile.stylistic_attributes?.tone || ''} 
                        onChange={(e) => handleUpdateStyle('tone', e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white text-sm focus:border-yellow-500 outline-none"
                    />
                </div>

                <div>
                    <label className="text-xs text-gray-400 mb-1 block">Reasoning Pattern</label>
                    <select 
                        value={profile.stylistic_attributes?.reasoning_pattern || 'Analytical'}
                        onChange={(e) => handleUpdateStyle('reasoning_pattern', e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white text-sm"
                    >
                        <option value="Analytical">Analytical</option>
                        <option value="Metaphorical">Metaphorical</option>
                        <option value="Socratic">Socratic</option>
                        <option value="Direct">Direct</option>
                    </select>
                </div>
                
                <div className="text-xs text-gray-500 italic">
                    Last calibrated: {new Date(profile.last_updated).toLocaleDateString()}
                </div>
            </div>
        </div>
    </div>
  );
}
