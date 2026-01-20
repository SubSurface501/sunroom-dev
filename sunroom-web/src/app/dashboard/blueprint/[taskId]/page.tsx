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

const nodeWidth = 356;
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


const ClientOnly = ({ children }: { children: React.ReactNode }) => {
    const [isMounted, setIsMounted] = useState(false);
    useEffect(() => {
        setIsMounted(true);
    }, []);

    if (!isMounted) {
        return null;
    }

    return <>{children}</>;
}

export default function BlueprintEditorPage() {
    const params = useParams();
    const taskId = params.taskId as string;
    const router = useRouter();

    const [status, setStatus] = useState<'POLLING' | 'READY' | 'RENDERING' | 'ERROR'>('POLLING');
    const [volumeId, setVolumeId] = useState<string | null>(null);
    const [volume, setVolume] = useState<StoryVolume | null>(null);
    const [logs, setLogs] = useState<string[]>(["Initializing Blueprint Protocol..."]);
    const [suggestion, setSuggestion] = useState<any>(null);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

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

    // Polling for Draft Completion
    useEffect(() => {
        // Early exit if we are already ready or rendering
        if (status !== 'POLLING') return;

        let intervalId: NodeJS.Timeout;
        let isMounted = true;

        const checkStatus = async () => {
            if (!isMounted) return;
            try {
                const { data: { session } } = await supabase.auth.getSession();
                if (!session) return;



                // OPTIMIZATION: First check if taskId is actually a Volume ID
                // This handles the "Return to Architect" flow and direct access
                const { data: existingVolume } = await supabase
                    .from('StoryVolumes')
                    .select('id')
                    .eq('id', taskId)
                    .maybeSingle();

                if (existingVolume) {
                    if (isMounted) {
                        setVolumeId(existingVolume.id);
                        setStatus('READY');
                        setLogs(prev => [...prev, "Volume Found. Loading Blueprint..."]);
                    }
                    return; // Stop polling
                }

                // If not a volume, poll the Task API
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${apiUrl}/api/v1/tasks/${taskId}`, {
                    headers: { 'Authorization': `Bearer ${session.access_token}` }
                });

                if (!res.ok) throw new Error("Failed to poll task");

                const data = await res.json();

                if (isMounted) {
                    if (data.status === 'SUCCESS') {
                        setVolumeId(data.result); // Result is volume_id
                        setStatus('READY');
                        setLogs(prev => [...prev, "Drafting Complete. Blueprint Available."]);
                    } else if (data.status === 'FAILURE') {
                        setStatus('ERROR');
                        setLogs(prev => [...prev, `Drafting Failed: ${data.result}`]);
                    } else {
                        // PENDING or STARTED - Keep polling
                    }
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        };

        // Run check immediately, then set interval
        checkStatus();
        intervalId = setInterval(checkStatus, 2000);

        return () => {
            isMounted = false;
            clearInterval(intervalId);
        };
    }, [taskId, status]);

    const getNodeColor = useCallback((n: Node) => {
        if (n.type === 'input') return '#eab308';
        if (n.type === 'output') return '#a855f7';
        return '#1f2937';
    }, []);

    const handleSuggestTwist = async () => {
        if (!volumeId) return;
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) return;
            
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiUrl}/api/v1/volumes/${volumeId}/suggest_complement`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ focus_node_id: selectedNodeId })
            });
            const data = await res.json();
            setSuggestion(data);
        } catch (e) {
            console.error("NSKP Failed", e);
        }
    };

    const handleGreenlight = async () => {
        if (!volumeId) return;
        setStatus('RENDERING');
        setLogs(prev => [...prev, "Greenlight received. Initializing Render Protocol..."]);

        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) return;

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            await fetch(`${apiUrl}/api/v1/volumes/${volumeId}/write`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${session.access_token}` }
            });

            // Navigate to player or just show status
            // For MVP, let's push back to dashboard after a moment
            setTimeout(() => {
                router.push(`/dashboard?highlightVolumeId=${volumeId}`);
            }, 3000);
        } catch (e) {
            console.error("Render trigger failed", e);
            setStatus('ERROR');
        }
    };

    const handleIllustrate = async () => {
        if (!volumeId) return;
        setLogs(prev => [...prev, "Illustration process initiated..."]);

        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) return;

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            await fetch(`${apiUrl}/api/v1/volumes/${volumeId}/illustrate`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${session.access_token}` }
            });
        } catch (e) {
            console.error("Illustration trigger failed", e);
        }
    };

    const handleDiscard = async () => {
        if (!volumeId) return;
        setLogs(prev => [...prev, "Discarding blueprint..."]);
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) return;

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiUrl}/api/v1/volumes/${volumeId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${session.access_token}` }
            });

            if (!res.ok) {
                throw new Error("Failed to delete volume");
            }
            setLogs(prev => [...prev, "Blueprint discarded. Redirecting..."]);
            router.push('/dashboard');
        } catch (e) {
            console.error("Discard failed", e);
            setLogs(prev => [...prev, `Discard failed: ${e}`]);
        }
    };

    return (
        <div className="h-screen bg-gray-900 flex flex-col text-white">
            {/* Header */}
            <div className="bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center shadow-md z-10">
                <div>
                    <h1 className="text-xl font-bold text-yellow-500 flex items-center gap-2">
                        <BrainCircuit className="w-6 h-6" />
                        Volume Architect
                    </h1>
                    <p className="text-sm text-gray-400">
                        {status === 'POLLING' ? 'Drafting Blueprint...' : 
                         status === 'READY' ? `Reviewing: ${volume?.title}` :
                         status === 'RENDERING' ? 'Rendering Content...' : 'System Error'}
                    </p>
                </div>
                
                {status === 'READY' && (
                    <div className="flex gap-4">
                        <button
                            onClick={handleSuggestTwist}
                            className="px-4 py-2 text-yellow-500 border border-yellow-500/50 hover:bg-yellow-500/10 rounded flex items-center gap-2 transition"
                        >
                            <Lightbulb className="w-4 h-4" />
                            {selectedNodeId ? 'Suggest Twist (Selected)' : 'Suggest Twist (End)'}
                        </button>
                        <button 
                            onClick={handleDiscard}
                            className="px-4 py-2 text-gray-300 hover:text-white transition"
                        >
                            Discard
                        </button>
                        <button 
                            onClick={handleGreenlight}
                            className="px-6 py-2 bg-green-600 hover:bg-green-500 text-white font-bold rounded shadow-lg flex items-center gap-2 animate-pulse"
                        >
                            <CheckCircle className="w-4 h-4" />
                            Greenlight & Render
                        </button>
                        <button 
                            onClick={handleIllustrate}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded shadow-lg flex items-center gap-2"
                        >
                            Illustrate
                        </button>
                    </div>
                )}
            </div>

            {/* Main Content Area */}
            <div className="flex-1 relative">
                {status === 'POLLING' && (
                    <div className="absolute inset-0 flex items-center justify-center flex-col gap-4 bg-gray-900/90 z-20">
                        <div className="w-16 h-16 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-yellow-500 font-mono animate-pulse">Consulting the Architect...</p>
                    </div>
                )}

                {status === 'RENDERING' && (
                    <div className="absolute inset-0 flex items-center justify-center flex-col gap-4 bg-black/90 z-20">
                         <Clock className="w-16 h-16 text-green-500 animate-bounce" />
                        <p className="text-green-500 font-bold text-xl">Production Started.</p>
                        <p className="text-gray-400">The agents are now writing and illustrating your story.</p>
                        <p className="text-xs text-gray-600">Redirecting to dashboard...</p>
                    </div>
                )}

                {/* React Flow Canvas */}
                <div className="w-full h-full bg-gray-900">
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onNodeClick={(_, node) => setSelectedNodeId(node.id)}
                        onPaneClick={() => setSelectedNodeId(null)}
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

                {/* Agent Logs Console */}
                <div className="absolute bottom-4 right-4 w-96 bg-black/80 border border-gray-700 rounded p-3 font-mono text-xs text-green-400 h-48 overflow-y-auto shadow-xl backdrop-blur-sm">
                    <div className="sticky top-0 bg-black/90 pb-2 border-b border-gray-800 mb-2 font-bold text-gray-500 uppercase flex justify-between">
                        <span>System Logs</span>
                        <span className="animate-pulse">● Live</span>
                    </div>
                    <div className="flex flex-col gap-1">
                        {logs.map((log, i) => (
                            <div key={i} className="break-words">
                                <ClientOnly>
                                    <span className="text-gray-600 mr-2">[{new Date().toISOString()}]</span>
                                </ClientOnly>
                                {log}
                            </div>
                        ))}
                        <div ref={(el) => el?.scrollIntoView({ behavior: 'smooth' })} />
                    </div>
                </div>

                {suggestion && (
                    <div className="absolute top-20 right-4 w-80 bg-gray-800 border border-yellow-500 p-4 rounded shadow-2xl z-50 animate-in slide-in-from-right">
                        <div className="flex justify-between items-start mb-2">
                            <h3 className="text-yellow-500 font-bold flex items-center gap-2">
                                <Lightbulb className="w-4 h-4" /> NSKP Suggestion
                            </h3>
                            <button onClick={() => setSuggestion(null)} className="text-gray-400 hover:text-white"><X className="w-4 h-4" /></button>
                        </div>
                        <p className="text-sm font-bold text-white mb-1">{suggestion.title || "New Concept"}</p>
                        <p className="text-xs text-gray-300 mb-4">{suggestion.summary || suggestion.suggestion}</p>
                        <button className="w-full py-1 bg-yellow-600 hover:bg-yellow-500 text-black font-bold text-xs rounded">
                            Add to Blueprint
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
