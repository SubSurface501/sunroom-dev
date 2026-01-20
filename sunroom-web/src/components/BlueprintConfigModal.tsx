'use client';

import React, { useState, useEffect } from 'react';

interface BlueprintConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (config: BlueprintConfig) => void;
    initialTitle: string;
    initialConcept: string;
}

export interface BlueprintConfig {
    title: string;
    root_concept: string;
    fidelity: number; // 0.0 to 1.0
    lenses: string[];
}

const BlueprintConfigModal: React.FC<BlueprintConfigModalProps> = ({ isOpen, onClose, onConfirm, initialTitle, initialConcept }) => {
    const [title, setTitle] = useState(initialTitle);
    const [concept, setConcept] = useState(initialConcept);
    const [fidelity, setFidelity] = useState(0.5);
    const [lenses, setLenses] = useState<string[]>([]);
    const [availableLenses, setAvailableLenses] = useState<{id: string, name: string}[]>([]);
    const [suggestions, setSuggestions] = useState<any[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);

    useEffect(() => {
        setTitle(initialTitle);
        setConcept(initialConcept);
    }, [initialTitle, initialConcept]);

    useEffect(() => {
        const token = localStorage.getItem('supabase_access_token');
        if (isOpen && token) {
            fetch('http://localhost:8000/api/v1/lenses', {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.json())
            .then(data => setAvailableLenses(data))
            .catch(err => console.error("Failed to fetch lenses", err));
        }
    }, [isOpen]);

    const handleSpark = async () => {
        const token = localStorage.getItem('supabase_access_token');
        if (!concept || !token) return;
        setLoadingSuggestions(true);
        setShowSuggestions(true);
        try {
            const response = await fetch('http://localhost:8000/api/v1/concepts/search', {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: concept, domain: "Science & Philosophy" })
            });
            const data = await response.json();
            setSuggestions(data.results || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const handleConfirm = () => {
        onConfirm({
            title,
            root_concept: concept,
            fidelity,
            lenses
        });
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="bg-[#1e1e2e] text-white rounded-xl shadow-2xl p-8 w-full max-w-2xl border border-gray-700 relative">
                <button 
                    onClick={onClose}
                    className="absolute top-4 right-4 text-gray-400 hover:text-white"
                >
                    ✕
                </button>

                <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                    <span>🏛️</span> Blueprint Configuration
                </h2>

                <div className="space-y-6">
                    {/* Title */}
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-1">Project Title</label>
                        <input 
                            type="text" 
                            value={title} 
                            onChange={(e) => setTitle(e.target.value)}
                            className="w-full bg-[#2a2a3c] border border-gray-600 rounded p-2 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>

                    {/* Concept + Spark */}
                    <div className="relative">
                        <label className="block text-sm font-medium text-gray-400 mb-1">Anchor Concept</label>
                        <div className="flex gap-2">
                            <input 
                                type="text" 
                                value={concept} 
                                onChange={(e) => setConcept(e.target.value)}
                                className="flex-grow bg-[#2a2a3c] border border-gray-600 rounded p-2 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                            <button 
                                onClick={handleSpark}
                                disabled={loadingSuggestions}
                                className="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded font-bold transition-colors"
                                title="Spark: Find complementary concepts"
                            >
                                {loadingSuggestions ? '⚡...' : '⚡ Spark'}
                            </button>
                        </div>
                        
                        {/* Suggestions Dropdown */}
                        {showSuggestions && (
                            <div className="absolute top-full left-0 right-0 mt-2 bg-[#2a2a3c] border border-gray-600 rounded-lg shadow-xl z-10 max-h-60 overflow-y-auto">
                                <div className="p-2 border-b border-gray-700 flex justify-between items-center">
                                    <span className="text-xs text-gray-400">Domain Suggestions</span>
                                    <button onClick={() => setShowSuggestions(false)} className="text-xs text-gray-400 hover:text-white">Close</button>
                                </div>
                                {suggestions.length === 0 ? (
                                    <div className="p-4 text-gray-500 text-sm text-center">No sparks found.</div>
                                ) : (
                                    suggestions.map((s, idx) => (
                                        <div 
                                            key={idx} 
                                            onClick={() => { setConcept(s.concept_name); setShowSuggestions(false); }}
                                            className="p-3 hover:bg-[#3b3b52] cursor-pointer border-b border-gray-700 last:border-0"
                                        >
                                            <div className="font-bold text-yellow-500">{s.concept_name}</div>
                                            <div className="text-xs text-gray-400 truncate">{s.definition}</div>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>

                    {/* Ego Slider */}
                    <div>
                        <div className="flex justify-between items-end mb-2">
                            <label className="block text-sm font-medium text-gray-400">Narrative Stance (Ego Slider)</label>
                            <span className="text-xs font-mono text-blue-400">λ = {fidelity.toFixed(2)}</span>
                        </div>
                        <input 
                            type="range" 
                            min="0" 
                            max="1" 
                            step="0.05" 
                            value={fidelity} 
                            onChange={(e) => setFidelity(parseFloat(e.target.value))}
                            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>Poetic / Subjective</span>
                            <span>Synthesis</span>
                            <span>Academic / Objective</span>
                        </div>
                    </div>

                    {/* Lenses */}
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-2">Active Lenses</label>
                        <div className="flex flex-wrap gap-2">
                            {availableLenses.map(lens => (
                                <button
                                    key={lens.id}
                                    onClick={() => {
                                        if (lenses.includes(lens.name)) {
                                            setLenses(lenses.filter(l => l !== lens.name));
                                        } else {
                                            setLenses([...lenses, lens.name]);
                                        }
                                    }}
                                    className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                                        lenses.includes(lens.name) 
                                        ? 'bg-blue-600 border-blue-500 text-white' 
                                        : 'bg-transparent border-gray-600 text-gray-400 hover:border-gray-400'
                                    }`}
                                >
                                    {lens.name}
                                </button>
                            ))}
                            {availableLenses.length === 0 && (
                                <span className="text-gray-600 italic text-sm">No lenses found. Run Auto-Genesis first.</span>
                            )}
                        </div>
                    </div>

                    {/* Action */}
                    <button 
                        onClick={handleConfirm}
                        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold py-4 rounded-lg shadow-lg transform transition hover:scale-[1.02]"
                    >
                        Generate Blueprint
                    </button>
                </div>
            </div>
        </div>
    );
};

export default BlueprintConfigModal;
