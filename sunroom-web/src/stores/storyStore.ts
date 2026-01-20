import { create } from 'zustand';
import { StoryVolume } from '@/types/schema';

// Add these types at the top
export interface GhostOption {
  title: string;
  summary: string;
  type: 'narrative_beat' | 'deep_dive' | 'twist';
  relationship: string;
}

interface StoryState {
  currentVolume: StoryVolume | null;
  currentNodeId: string | null;
  history: string[]; // List of Node IDs visited (Stack)
  inventory: string[]; // Items collected
  navigationDirection: 'forward' | 'backward'; // Track direction for page placement
  ghostOptions: GhostOption[]; // <--- New state to hold the suggestions
  isExpanding: boolean;        // <--- Loading state for the AI generation
  
  // Actions
  setVolume: (volume: StoryVolume) => void;
  
  // Navigation
  visitNode: (nextNodeId: string) => void; // Go Forward
  backNode: () => void; // Go Backward
  
  // Raw Setters (Use carefully)
  setCurrentNode: (nodeId: string) => void;
  resetStory: () => void;
  expandNode: (nodeId: string, branchId: string) => Promise<void>;
  materializeGhost: (parentNodeId: string, option: GhostOption) => Promise<void>;
  clearGhosts: () => void;
}

export const useStoryStore = create<StoryState>((set, get) => ({
  currentVolume: null,
  currentNodeId: null,
  history: [],
  inventory: [],
  navigationDirection: 'forward',
  ghostOptions: [],
  isExpanding: false,

  setVolume: (volume) => set({ currentVolume: volume, history: [], currentNodeId: null, navigationDirection: 'forward' }), // Reset history on new volume
  
  setCurrentNode: (nodeId) => set({ currentNodeId: nodeId }), // Raw setter

  visitNode: (nextNodeId) => set((state) => {
      if (state.currentNodeId) {
          return {
              history: [...state.history, state.currentNodeId],
              currentNodeId: nextNodeId,
              navigationDirection: 'forward'
          };
      }
      return { currentNodeId: nextNodeId, navigationDirection: 'forward' }; // First node, nothing to push
  }),

  backNode: () => set((state) => {
      if (state.history.length === 0) return {}; // Nowhere to go
      const newHistory = [...state.history];
      const prevNodeId = newHistory.pop();
      return {
          history: newHistory,
          currentNodeId: prevNodeId,
          navigationDirection: 'backward'
      };
  }),

  resetStory: () => set({ currentNodeId: null, history: [], inventory: [], navigationDirection: 'forward' }),

  expandNode: async (nodeId: string, branchId: string) => {
    set({ isExpanding: true, ghostOptions: [] }); // Reset previous ghosts
    try {
      const response = await fetch('http://localhost:8000/api/v1/nodes/expand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          volume_id: get().currentVolume?.id, // Assuming you store this
          node_id: nodeId, 
          branch_id: branchId 
        }),
      });

      if (!response.ok) throw new Error('Expansion failed');
      
      const data = await response.json();
      set({ ghostOptions: data.options });
    } catch (error) {
      console.error("Failed to expand node:", error);
    } finally {
      set({ isExpanding: false });
    }
  },

  materializeGhost: async (parentNodeId: string, option: GhostOption) => {
    set({ isExpanding: true });
    try {
        const volumeId = get().currentVolume?.id; 
        if (!volumeId) throw new Error("No active volume");
        
        const response = await fetch('http://localhost:8000/api/v1/nodes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                volume_id: volumeId,
                parent_node_id: parentNodeId,
                branch_id: 'main', // Hardcoded for MVP
                title: option.title,
                summary: option.summary,
                type: option.type,
                relationship_type: option.relationship
            }),
        });

        if (!response.ok) throw new Error('Failed to materialize node');
        
        // Success! Clear ghosts and refresh the graph
        set({ ghostOptions: [] });
        
        // TODO: Trigger graph refresh (get().fetchGraph(volumeId) if available)
        
    } catch (error) {
        console.error("Error creating node:", error);
    } finally {
        set({ isExpanding: false });
    }
  },

  clearGhosts: () => set({ ghostOptions: [] }),
}));
