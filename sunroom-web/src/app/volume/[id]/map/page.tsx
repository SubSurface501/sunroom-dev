'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import ReactFlow, { 
    useNodesState, 
    useEdgesState, 
    Background, 
    Controls, 
    MiniMap,
    MarkerType,
    Node,
    Edge
} from 'reactflow';
import 'reactflow/dist/style.css';
import { BrainCircuit, CheckCircle, Lightbulb, Clock, X } from 'lucide-react';
import dagre from 'dagre';

import StoryNode from '@/components/graph/StoryNode'; // Import the custom node
import { supabase } from '@/lib/supabase';
import { StoryVolume, GraphNode, GraphConnection } from '@/types/schema';

// Define nodeTypes outside the component to prevent re-creation on render
const nodeTypes = { 
    input: StoryNode, 
    default: StoryNode, 
    output: StoryNode 
};

const nodeWidth = 250;
const nodeHeight = 150;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodesep = 100;
  const ranksep = 120;

  console.log("Layout config:", { nodeWidth, nodeHeight, nodesep, ranksep });

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: nodesep, 
    ranksep: ranksep
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
  });

  return { nodes, edges };
};


export default function VolumeMapPage() {
    const params = useParams();
    const volumeId = params.id as string;

    const router = useRouter();

    const [status, setStatus] = useState<'READY' | 'ERROR'>('READY');
    const [volume, setVolume] = useState<StoryVolume | null>(null);

    // React Flow State
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // Fetch Volume Data and Layout Graph
    useEffect(() => {
        if (status === 'READY' && volumeId) {
            const fetchAndLayout = async () => {
                const { data, error } = await supabase
                    .from('StoryVolumes')
                    .select('*')
                    .eq('id', volumeId)
                    .single();
                
                if (data && data.graph_structure) {
                    setVolume(data);
                    
                    const { nodes: graphNodes, connections: graphConnections } = data.graph_structure;

                    console.log("Graph Nodes:", graphNodes);

                    if (!graphNodes || !graphConnections) {
                        console.error("Invalid graph structure received:", data.graph_structure);
                        return;
                    }
                    
                    const initialNodes: Node[] = graphNodes.map((node: GraphNode) => ({
                        id: node.node_id,
                        type: node.type === 'root' ? 'input' : 'default',
                        data: {
                            title: node.title,
                            summary: node.content.summary,
                            novelty_score: (node as any).novelty_score || 0.5,
                            type: node.type,
                        },
                        position: { x: 0, y: 0 },
                        style: {
                            width: nodeWidth,
                        }
                    }));

                    const initialEdges: Edge[] = graphConnections.map((conn: GraphConnection) => ({
                        id: `${conn.from}-${conn.to}`,
                        source: conn.from,
                        target: conn.to,
                        label: conn.choice_label,
                        type: 'smoothstep',
                        animated: true,
                        style: { stroke: '#6b7280', strokeWidth: 2 },
                        labelStyle: { fill: 'black', fontWeight: 700 },
                        markerEnd: { type: MarkerType.ArrowClosed, color: '#6b7280' },
                    }));
                    
                    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(initialNodes, initialEdges);
                    
                    setNodes(layoutedNodes);
                    setEdges(layoutedEdges);
                }
            };

            fetchAndLayout();
        }
    }, [status, volumeId, setNodes, setEdges]);

    const getNodeColor = useCallback((n: Node) => {
        if (n.type === 'input') return '#eab308';
        if (n.type === 'output') return '#a855f7';
        return '#1f2937';
    }, []);

    return (
        <div className="h-screen bg-gray-900 flex flex-col text-white">
            {/* Header */}
            <div className="bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center shadow-md z-10">
                <div>
                    <h1 className="text-xl font-bold text-yellow-500 flex items-center gap-2">
                        <BrainCircuit className="w-6 h-6" />
                        Volume Map
                    </h1>
                    <p className="text-sm text-gray-400">
                        { `Reviewing: ${volume?.title}` }
                    </p>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 relative">
                {/* React Flow Canvas */}
                <div className="w-full h-full bg-gray-900">
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        fitView
                        attributionPosition="bottom-right"
                        nodeTypes={nodeTypes} // Pass the memoized node types
                    >
                        <Background color="#374151" gap={16} />
                        <Controls className="bg-gray-800 border-gray-700 text-white" />
                        <MiniMap 
                            nodeColor={getNodeColor}
                            className="bg-gray-800 border-gray-700" 
                        />
                    </ReactFlow>
                </div>

                {/* Legend Overlay */}
                <div className="absolute bottom-4 left-4 bg-gray-800 p-4 rounded shadow-lg border border-gray-700 opacity-90">
                    <h3 className="text-xs font-bold text-gray-400 mb-2 uppercase">Joint Types</h3>
                    <div className="space-y-2 text-xs">
                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-red-500 rounded-full"></div> Divergence (Choice)</div>
                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-orange-500 rounded-full"></div> Escalation (Risk)</div>
                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-blue-500 rounded-full"></div> Inquiry (Lore)</div>
                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-purple-500 rounded-full"></div> Convergence (Fate)</div>
                    </div>
                </div>
            </div>
        </div>
    );
}