"use client";

import { useState, useEffect, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { Loader2, BookOpen, ChevronRight, ChevronLeft } from 'lucide-react';

export default function PlayStoryPlayerPage() {
    const params = useParams();
    const router = useRouter();
    const volumeId = params.volumeId as string;

    const [loading, setLoading] = useState(true);
    const [storyMap, setStoryMap] = useState<any>(null);
    const [storyNodes, setStoryNodes] = useState<any[]>([]);
    const [currentNodeId, setCurrentNodeId] = useState<string | null>(null);
    const [currentPageIndex, setCurrentPageIndex] = useState(0); // New state for pagination within a node
    const [history, setHistory] = useState<string[]>([]);

    useEffect(() => {
        const loadVolume = async () => {
            setLoading(true);
            const [volumeRes, nodesRes] = await Promise.all([
                supabase.from('StoryVolumes').select('*').eq('id', volumeId).single(),
                supabase.from('Nodes').select('id, type, content, volume_id, title').eq('volume_id', volumeId)
            ]);

            const { data: volumeData, error: volumeError } = volumeRes;
            const { data: nodesData, error: nodesError } = nodesRes;

            if (volumeError || nodesError) {
                console.error("Error loading story:", volumeError || nodesError);
                setLoading(false);
                return;
            }

            if (volumeData && volumeData.graph_structure && nodesData) {
                setStoryMap(volumeData.graph_structure);
                setStoryNodes(nodesData);
                
                const rootNode = volumeData.graph_structure.nodes.find((n: any) => n.type === 'root');
                if (rootNode) {
                    setCurrentNodeId(rootNode.node_id);
                    setCurrentPageIndex(0); // Reset page index for new node
                }
            }
            setLoading(false);
        };

        if (volumeId) {
            loadVolume();
        }
    }, [volumeId]);

    const currentNode = useMemo(() => {
        if (storyNodes.length > 0 && currentNodeId) {
            return storyNodes.find((n: any) => n.id === currentNodeId);
        }
        return null;
    }, [storyNodes, currentNodeId]);

    const handleChoice = (targetId: string) => {
        setHistory([...history, currentNodeId!]);
        setCurrentNodeId(targetId);
        setCurrentPageIndex(0); // Reset page index for new node
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handlePageTurn = (direction: 'next' | 'prev') => {
        if (direction === 'next') {
            setCurrentPageIndex(prev => prev + 1);
        } else {
            setCurrentPageIndex(prev => prev - 1);
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };
    
    if (loading) {
        return (
            <div className="h-screen w-full bg-[#fdf6e3] flex items-center justify-center">
                <Loader2 className="w-12 h-12 text-[#b58900] animate-spin" />
            </div>
        );
    }

    if (!currentNode || !storyMap) {
        return <div className="p-10 text-center text-gray-500 bg-[#fdf6e3]">Loading story map...</div>;
    }

    const displayTitle = currentNode?.title || 'Untitled Chapter';
    const pages = currentNode.content?.pages || [];
    const currentPage = pages[currentPageIndex];
    const isLastPage = currentPageIndex === pages.length - 1;

    const choices = storyMap.connections.filter((c: any) => c.from === currentNodeId);

    return (
        <div className="min-h-screen bg-[#F2E6B6] text-[#657b83] font-mono selection:bg-[#b58900] selection:text-white">
            
            <nav className="sticky top-0 z-10 bg-[#eee8d5]/90 backdrop-blur-sm border-b border-[#d3cbb7] px-6 py-3 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <BookOpen className="w-5 h-5 text-[#b58900]" />
                    <span className="uppercase tracking-widest text-sm font-bold text-[#b58900]">
                        The Sun Room Archives
                    </span>
                </div>
                <button 
                    onClick={() => router.push('/dashboard')}
                    className="text-xs uppercase tracking-widest hover:text-[#b58900] transition-colors"
                >
                    Close Volume
                </button>
            </nav>

            <main className="max-w-3xl mx-auto py-12 px-6 md:px-12">
                
                <header className="mb-12 text-center border-b-2 border-[#b58900] pb-8">
                    <h1 className="text-3xl md:text-4xl font-bold text-[#073642] uppercase tracking-widest mb-2">
                        {displayTitle}
                    </h1>
                    <p className="text-sm text-[#93a1a1]">Page {currentPageIndex + 1} of {pages.length}</p>
                </header>

                {currentPage?.image_url ? (
                    <div className="mb-12 border-4 border-[#073642] p-2 bg-white shadow-xl rotate-1 transform hover:rotate-0 transition-transform duration-500">
                        <img 
                            src={currentPage.image_url} 
                            alt={`Illustration for page ${currentPageIndex + 1}`}
                            className="w-full h-auto grayscale-[20%] sepia-[30%] contrast-125"
                        />
                    </div>
                ) : (
                     <div className="mb-12 h-64 bg-[#eee8d5] border-2 border-dashed border-[#93a1a1] flex items-center justify-center text-[#93a1a1] uppercase text-sm tracking-widest">
                        [ Illustration Pending ]
                    </div>
                )}

                <article className="prose prose-lg prose-p:text-[#657b83] prose-headings:text-[#073642] max-w-none text-justify leading-relaxed mb-16">
                    <p>{currentPage?.narrative_text || '...The pages are blank...'}</p>
                </article>

                {/* --- NAVIGATION & CHOICES --- */}
                <section className="space-y-6 mt-12 pt-12 border-t border-[#d3cbb7]">
                    {isLastPage ? (
                        <>
                            <h3 className="text-center text-sm uppercase tracking-widest text-[#93a1a1] mb-8">
                                — How do you proceed? —
                            </h3>
                            <div className="grid gap-4">
                                {choices.map((choice: any) => (
                                    <button
                                        key={`${choice.from}-${choice.to}`}
                                        onClick={() => handleChoice(choice.to)}
                                        className="group relative w-full text-left p-6 border-2 border-[#073642] hover:bg-[#073642] hover:text-[#fdf6e3] transition-all duration-300 ease-in-out"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-bold text-lg font-mono">
                                                {choice.choice_label}
                                            </span>
                                            <ChevronRight className="w-5 h-5 opacity-0 group-hover:opacity-100 transform -translate-x-2 group-hover:translate-x-0 transition-all" />
                                        </div>
                                    </button>
                                ))}
                            </div>
                            {choices.length === 0 && (
                                <div className="text-center mt-10">
                                    <p className="text-[#cb4b16] font-bold uppercase tracking-widest">The End.</p>
                                    <button 
                                        onClick={() => router.push('/dashboard')}
                                        className="mt-4 text-sm underline hover:text-[#b58900]"
                                    >
                                        Return to Library
                                    </button>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="flex justify-between items-center">
                            <button
                                onClick={() => handlePageTurn('prev')}
                                disabled={currentPageIndex === 0}
                                className="flex items-center gap-2 px-6 py-3 border-2 border-[#073642] disabled:opacity-50 hover:bg-[#073642] hover:text-[#fdf6e3] transition-all"
                            >
                                <ChevronLeft size={16} /> Previous
                            </button>
                            <button
                                onClick={() => handlePageTurn('next')}
                                className="flex items-center gap-2 px-6 py-3 border-2 border-[#073642] hover:bg-[#073642] hover:text-[#fdf6e3] transition-all"
                            >
                                Next <ChevronRight size={16} />
                            </button>
                        </div>
                    )}
                </section>
            </main>
        </div>
    );
}