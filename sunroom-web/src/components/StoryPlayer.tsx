import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { useStoryStore } from '@/stores/storyStore';
import { Trailhead, TrailheadPage, GraphNode } from '@/types/schema';
import { motion, AnimatePresence } from 'framer-motion';
import { HomeIcon, RotateCcwIcon, Eye, EyeOff } from 'lucide-react';
import { SourceInspector } from './SourceInspector';

export default function StoryPlayer({ volumeId }: { volumeId: string }) {
  const { currentVolume, currentNodeId, setVolume, setCurrentNode, visitNode, backNode, history, navigationDirection } = useStoryStore();
  const [activeTrailhead, setActiveTrailhead] = useState<Trailhead | null>(null);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [nodeMap, setNodeMap] = useState<Record<string, string>>({});
  const [uiVisible, setUiVisible] = useState(true);
  const [showInspector, setShowInspector] = useState(false);
  const router = useRouter();

  // Initialize Volume
  useEffect(() => {
    async function init() {
      if (!volumeId) return;
      
      const { data: volume, error } = await supabase
        .from('StoryVolumes')
        .select('*')
        .eq('id', volumeId)
        .single();

      if (error || !volume) {
        console.error("Failed to load volume", error);
        return;
      }

      setVolume(volume);

      // Identify Root Node if not already set
      if (volume.graph_structure?.nodes) {
        const root = volume.graph_structure.nodes.find((n: GraphNode) => n.type === 'root');
        if (root && !currentNodeId) {
            setCurrentNode(root.node_id);
        }
      }
    }
    init();
  }, [volumeId, setVolume]); // Removed currentNodeId dependency to prevent loops

  // Fetch Node Content when currentNodeId changes
  useEffect(() => {
      async function fetchNode() {
          if (!currentNodeId) return;
          setLoading(true);
          
          const { data: node, error } = await supabase
              .from('StoryNodes') // Assuming 'StoryNodes' is the correct table
              .select('*')
              .eq('id', currentNodeId)
              .single();
              
          if (node) {
              setActiveTrailhead({
                  id: node.id,
                  title: node.title || 'Untitled',
                  content: node.content,
                  status: node.status
              });
              setCurrentPageIndex(0);
              visitNode(node.id);
          } else {
              console.error("Node not found:", error);
          }
          setLoading(false);
      }
      fetchNode();
  }, [currentNodeId, visitNode]);

  const currentPage = useMemo(() => {
      if (!activeTrailhead?.content?.pages) return null;
      return activeTrailhead.content.pages[currentPageIndex];
  }, [activeTrailhead, currentPageIndex]);

  const currentImageUrl = currentPage?.image_url;

  const isLastPage = useMemo(() => {
      if (!activeTrailhead?.content?.pages) return true;
      return currentPageIndex >= activeTrailhead.content.pages.length - 1;
  }, [activeTrailhead, currentPageIndex]);

  const choices = useMemo(() => {
      if (!currentVolume?.graph_structure?.connections || !currentNodeId) return [];
      return currentVolume.graph_structure.connections.filter((c: any) => c.from === currentNodeId);
  }, [currentVolume, currentNodeId]);

  const handleNextPage = () => {
      if (activeTrailhead && currentPageIndex < (activeTrailhead.content.pages.length - 1)) {
          setCurrentPageIndex(prev => prev + 1);
      }
  };

  const handlePrevPage = () => {
      if (currentPageIndex > 0) {
          setCurrentPageIndex(prev => prev - 1);
      } else if (history.length > 0) {
          backNode();
      }
  };

  const handleChoice = (targetNodeId: string) => {
      setCurrentNode(targetNodeId);
  };

  if (loading && !activeTrailhead) {
      return <div className="flex items-center justify-center h-screen bg-black text-white">Loading Story...</div>;
  }

  if (!currentPage) return <div className="h-screen bg-black text-white">No content available.</div>;

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden font-serif text-white">
      
      {/* 1. Background Layer (The Art) */}
      <AnimatePresence mode='popLayout'>
        <motion.div 
          key={currentImageUrl || 'default'}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.5, ease: "easeInOut" }}
          className="absolute inset-0 z-0"
        >
          {currentImageUrl && (
            <img 
              src={currentImageUrl} 
              alt="Scene" 
              className="w-full h-full object-cover" 
            />
          )}
        </motion.div>
      </AnimatePresence>

      {/* 2. Cinematic Scrim */}
      <motion.div 
        animate={{ opacity: uiVisible ? 1 : 0 }}
        className="absolute inset-0 z-10 bg-gradient-to-t from-black via-black/60 to-transparent pointer-events-none"
      />

      {/* 3. UI Layer */}
      <div className="absolute inset-0 z-20 flex flex-col justify-between p-6 pointer-events-none">
          
          {/* Top Bar: Navigation & Toggle */}
          <div className="flex justify-between items-start pointer-events-auto">
              <button onClick={() => router.push('/dashboard')} className="text-white/50 hover:text-white transition">
                  <HomeIcon />
              </button>
              
              <div className="flex gap-2">
                  <button 
                    onClick={() => setShowInspector(!showInspector)} 
                    className={`text-white/50 hover:text-white transition bg-black/20 p-2 rounded-full backdrop-blur-sm ${showInspector ? 'text-emerald-400 bg-emerald-900/30' : ''}`}
                    title="Toggle Source Inspector"
                  >
                      🔍
                  </button>
                  <button 
                    onClick={() => setUiVisible(!uiVisible)} 
                    className="text-white/50 hover:text-white transition bg-black/20 p-2 rounded-full backdrop-blur-sm"
                    title={uiVisible ? "Hide Text" : "Show Text"}
                  >
                      {uiVisible ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
              </div>
          </div>

          {/* Source Inspector Panel (Absolute Right) */}
          <AnimatePresence>
            {uiVisible && showInspector && currentNodeId && (
                <motion.div
                    initial={{ x: 300, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 300, opacity: 0 }}
                    className="absolute right-6 top-20 w-80 bg-black/80 backdrop-blur-md border border-gray-700 p-4 rounded-lg shadow-2xl pointer-events-auto max-h-[60vh] overflow-y-auto"
                >
                    {/* <SourceInspector nodeId={currentNodeId} /> */}
                </motion.div>
            )}
          </AnimatePresence>

          {/* Bottom Bar: Narrative & Controls */}
          <motion.div 
            animate={{ opacity: uiVisible ? 1 : 0, y: uiVisible ? 0 : 20 }}
            className="flex flex-col items-center justify-end pb-8 md:pb-16 pointer-events-auto"
          >
            <div className="w-full max-w-3xl relative min-h-[200px]">
                <AnimatePresence mode='wait'>
                    <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    key={`${currentNodeId}-${currentPageIndex}`}
                    className="text-center w-full absolute bottom-0"
                    style={{ position: 'relative' }} 
                    >
                    <p className="text-xl md:text-2xl text-gray-100 leading-relaxed drop-shadow-lg mb-8 font-medium text-shadow-sm">
                        {currentPage.narrative_text}
                    </p>

                    <div className="flex gap-4 justify-center">
                        {/* Back Button */}
                        {(currentPageIndex > 0 || history.length > 0) && (
                            <button 
                                onClick={handlePrevPage}
                                className="px-6 py-3 border border-white/20 hover:bg-white/5 text-white/80 rounded transition backdrop-blur-md font-sans tracking-widest text-sm uppercase"
                            >
                                Back
                            </button>
                        )}

                        {!isLastPage ? (
                        <button 
                            onClick={handleNextPage}
                            className="px-8 py-3 border border-white/40 hover:bg-white/10 text-white rounded transition backdrop-blur-md font-sans tracking-widest text-sm uppercase"
                        >
                            Continue
                        </button>
                        ) : (
                        <div className="flex flex-col gap-3 items-center w-full">
                            {choices.length > 0 ? (
                                <>
                                    <div className="flex gap-4 flex-wrap justify-center">
                                    {choices.map((choice: any) => (
                                        <button
                                        key={choice.to}
                                        onClick={() => handleChoice(choice.to)} 
                                        className="px-6 py-4 bg-black/60 hover:bg-yellow-900/60 border border-yellow-500/30 hover:border-yellow-500/80 text-yellow-50 rounded-lg transition backdrop-blur-md shadow-xl hover:scale-105 transform duration-200 flex flex-col items-center min-w-[200px]"
                                        >
                                            <span className="text-lg font-bold">{choice.choice_label}</span>
                                        </button>
                                    ))}
                                    </div>
                                </>
                            ) : (
                                <p className="text-xl text-yellow-500 font-serif italic">The End.</p>
                            )}
                        </div>
                        )}
                    </div>
                    </motion.div>
                </AnimatePresence>
            </div>
          </motion.div>
      </div>
    </div>
  );
}