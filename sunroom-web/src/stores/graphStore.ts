import { create } from 'zustand';
import { Node, Edge, XYPosition } from 'reactflow';
import axios from 'axios';
import { getApiUrl } from '@/lib/utils';
import { useAuth } from '@/components/AuthContext'; // Assume AuthContext exists

const API_URL = getApiUrl();

interface NodeData { // This should match your backend Node schema (or a subset)
  id: string;
  volume_id: string;
  branch_id: string;
  title: string;
  type: string;
  content: { summary?: string; full_text?: string; novelty_score?: number; feedback?: string; choice_label?: string };
  context_snapshot?: string;
  created_at?: string;
  updated_at?: string;
}

interface EdgeData { // This should match your backend Edge schema
  id: string;
  volume_id: string;
  source_node_id: string;
  target_node_id: string;
  type: string;
  label?: string;
  created_at?: string;
}

interface BranchData { // This should match your backend Branch schema
  id: string;
  volume_id: string;
  name: string;
  head_node_id?: string;
  parent_branch_id?: string;
  divergence_point_node_id?: string;
  is_active: boolean;
  created_at?: string;
}

interface GraphState {
  nodes: Node[];
  edges: Edge[];
  branches: BranchData[];
  activeBranchId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchGraph: (volumeId: string, token: string) => Promise<void>;
  addNode: (nodeData: NodeData, token: string) => Promise<void>;
  updateNodePosition: (nodeId: string, position: XYPosition) => void;
  // More actions for edges, branches, ghost nodes, etc. will go here
}

export const useGraphStore = create<GraphState>((set, get) => ({
  nodes: [],
  edges: [],
  branches: [],
  activeBranchId: null,
  isLoading: false,
  error: null,

  fetchGraph: async (volumeId: string, token: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const headers = { Authorization: `Bearer ${token}` };

      const [nodesRes, edgesRes, branchesRes] = await Promise.all([
        axios.get(`${API_URL}/api/v1/volumes/${volumeId}/nodes`, { headers }),
        axios.get(`${API_URL}/api/v1/volumes/${volumeId}/edges`, { headers }),
        axios.get(`${API_URL}/api/v1/volumes/${volumeId}/branches`, { headers }),
      ]);

      const fetchedNodes: Node[] = nodesRes.data.map((dbNode: NodeData) => ({
        id: dbNode.id,
        position: { x: Math.random() * 500, y: Math.random() * 500 }, // Placeholder: will be replaced by layout algorithm
        data: { ...dbNode.content, title: dbNode.title, type: dbNode.type, volume_id: dbNode.volume_id, branch_id: dbNode.branch_id },
        type: 'default', // Will be custom node types later
        // You might want to store more data from dbNode in `data` field
      }));

      const fetchedEdges: Edge[] = edgesRes.data.map((dbEdge: EdgeData) => ({
        id: dbEdge.id,
        source: dbEdge.source_node_id,
        target: dbEdge.target_node_id,
        label: dbEdge.label || dbEdge.type,
        type: 'default', // Will be custom edge types later
      }));

      const fetchedBranches: BranchData[] = branchesRes.data;
      const mainBranch = fetchedBranches.find(b => b.name === 'main');

      set({ 
        nodes: fetchedNodes, 
        edges: fetchedEdges, 
        branches: fetchedBranches, 
        activeBranchId: mainBranch?.id || null,
        isLoading: false 
      });
    } catch (error) {
      console.error("Failed to fetch graph:", error);
      set({ error: "Failed to load graph data.", isLoading: false });
    }
  },

  addNode: async (nodeData: NodeData, token: string) => {
    set({ isLoading: true, error: null });
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.post(`${API_URL}/api/v1/volumes/${nodeData.volume_id}/nodes`, nodeData, { headers });
      const newNode = response.data;
      // Optimistically add to UI, then refresh or reconcile
      set((state) => ({
        nodes: state.nodes.concat({
          id: newNode.id,
          position: { x: Math.random() * 500, y: Math.random() * 500 },
          data: { ...newNode.content, title: newNode.title, type: newNode.type, volume_id: newNode.volume_id, branch_id: newNode.branch_id },
          type: 'default',
        }),
        isLoading: false,
      }));
    } catch (error) {
      console.error("Failed to add node:", error);
      set({ error: "Failed to add node.", isLoading: false });
    }
  },

  updateNodePosition: (nodeId: string, position: XYPosition) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, position } : node
      ),
    }));
    // In a real app, you'd debounce this and send to backend
  },

  // TODO: Add more actions for edges, branches, updating node content, deleting, etc.
}));
