'use client';

import React, { useEffect, useState, useCallback } from 'react';
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
} from 'reactflow';
import dagre from 'dagre';
import axios from 'axios';
import 'reactflow/dist/style.css';
import { useAuth } from '@/components/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface GraphViewProps {
  volumeId: string;
  currentEpoch: number; // Added Prop for Time Filtering
}

const nodeWidth = 250;
const nodeHeight = 150;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 80,
    ranksep: 150,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
    return node;
  });

  return { nodes: layoutedNodes, edges };
};

// Custom Node Component
const CustomNode = ({ data }: { data: any }) => {
    const nodeColor = () => {
        if (data.type === 'thought') return 'border-purple-500 bg-purple-900/50';
        if (data.type === 'collaborative_transcript') return 'border-cyan-400 bg-cyan-900/50';
        return 'border-slate-500 bg-slate-800';
    };

    return (
        <div className={`rounded-lg p-3 border-2 ${nodeColor()}`} style={{width: nodeWidth, height: nodeHeight, overflow: 'hidden'}}>
            <div className="text-white text-xs font-bold mb-2">{data.type.replace('_', ' ').toUpperCase()}</div>
            <div className="text-slate-300 text-xs" style={{ maxHeight: '100px', overflowY: 'auto'}}>{data.full_text}</div>
        </div>
    );
};

const nodeTypes = {
  custom: CustomNode,
};

export const GraphView: React.FC<GraphViewProps> = ({ volumeId, currentEpoch }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoadingGraph, setIsLoadingGraph] = useState(true);

  const { user, session } = useAuth();

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const fetchGraph = useCallback(async () => {
    setIsLoadingGraph(true);
    try {
      const res = await axios.get(`${API_URL}/api/v1/volumes/${volumeId}/graph`);
      const { nodes: apiNodes, links: apiEdges } = res.data;

      // --- NEW LOGIC: Filter by Epoch ---
      const visibleApiNodes = apiNodes.filter((n: any) => {
          // If node has no epoch data, assume it's visible (0), otherwise check against currentEpoch
          const nodeEpoch = n.valid_from_epoch || 0;
          return nodeEpoch <= currentEpoch;
      });

      // Filter edges: Only show if both Source and Target are visible
      const visibleNodeIds = new Set(visibleApiNodes.map((n: any) => n.id));
      const visibleApiEdges = apiEdges.filter((e: any) => 
          visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
      );
      // ----------------------------------

      const transformedNodes: Node[] = visibleApiNodes.map((node: any) => ({
        id: node.id.toString(),
        type: 'custom',
        data: { full_text: node.full_text, type: node.type },
        position: { x: 0, y: 0 },
      }));

      const transformedEdges: Edge[] = visibleApiEdges.map((edge: any) => ({
        id: `e${edge.source}-${edge.target}`,
        source: edge.source.toString(),
        target: edge.target.toString(),
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#475569' },
      }));

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        transformedNodes,
        transformedEdges
      );
      
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
      setIsLoadingGraph(false);

    } catch (e) {
      console.error("Graph fetch failed", e);
      setIsLoadingGraph(false);
    }
  }, [volumeId, currentEpoch, setNodes, setEdges, setIsLoadingGraph]);

  // --- RESTORED: The Initial Node Creation Logic ---
  const handleCreateInitialNode = useCallback(async () => {
    if (!volumeId || !user || !session) {
      console.error("Missing volumeId, user, or session to create initial node.");
      return;
    }

    try {
      const token = session.access_token;
      let branchId: string;

      const branchesRes = await axios.get(`${API_URL}/api/v1/volumes/${volumeId}/branches`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const existingBranches = branchesRes.data;

      if (existingBranches && existingBranches.length > 0) {
        const mainBranch = existingBranches.find((b: any) => b.name === 'main');
        branchId = mainBranch ? mainBranch.id : existingBranches[0].id;
        console.log(`Using existing branch: ${branchId}`);
      } else {
        const createBranchRes = await axios.post(`${API_URL}/api/v1/volumes/${volumeId}/branches`, 
          { name: 'main', volume_id: volumeId },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        branchId = createBranchRes.data.id;
        console.log(`Created new branch: ${branchId}`);
      }

      const newNodePayload = {
        volume_id: volumeId,
        branch_id: branchId,
        title: "Initial Thought/Concept",
        type: 'thought',
        content: {
          full_text: "This is the starting point of your narrative. Double-click to edit.",
          summary: "Starting point.",
        },
      };

      const response = await axios.post(`${API_URL}/api/v1/volumes/${volumeId}/nodes`, newNodePayload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const createdNode = response.data;

      const newReactFlowNode: Node = {
        id: createdNode.id.toString(),
        type: 'custom',
        data: { full_text: createdNode.content.full_text, type: createdNode.type },
        position: { x: 0, y: 0 },
      };

      setNodes((nds) => [...nds, newReactFlowNode]);
      fetchGraph(); 

    } catch (error) {
      console.error("Failed to create initial node:", error);
    }
  }, [volumeId, user, session, setNodes, fetchGraph]);

  useEffect(() => {
    if (volumeId) {
      fetchGraph();
      const interval = setInterval(fetchGraph, 10000);
      return () => clearInterval(interval);
    }
  }, [volumeId, currentEpoch, fetchGraph]);

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700 shadow-2xl h-[600px] mt-8 relative" style={{ width: '100%', height: '600px' }}>
        <div className="absolute top-4 left-4 z-10 bg-slate-900/80 p-2 rounded text-xs text-slate-300 pointer-events-none border border-slate-700">
            <div className="flex items-center gap-2 mb-1"><span className="text-purple-400 font-bold">●</span> System 2 Thought</div>
            <div className="flex items-center gap-2 mb-1"><span className="text-cyan-400 font-bold">●</span> Braid Transcript</div>
            <div className="flex items-center gap-2"><span className="text-slate-500 font-bold">●</span> Raw Atom</div>
        </div>
        {isLoadingGraph ? (
            <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-slate-400">Loading graph...</p>
            </div>
        ) : nodes.length === 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
                <p className="text-slate-400 text-lg font-semibold mb-2">No graph data available for this volume yet.</p>
                <p className="text-slate-500 text-sm mb-4">Start creating nodes in the Studio to see your thoughts unfold.</p>
                <button 
                  className="bg-purple-600 hover:bg-purple-500 text-white font-bold py-2 px-4 rounded-lg shadow-lg transition-all"
                  onClick={handleCreateInitialNode}
                >
                  Create Initial Node
                </button>
            </div>
        ) : (
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes}
                fitView
            >
                <Controls />
                <Background color="#334155" gap={16} />
            </ReactFlow>
        )}
    </div>
  );
};