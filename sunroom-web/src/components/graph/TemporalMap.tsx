"use client";

import React, { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  Panel,
  Position,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';
import { useAuth } from '@/components/AuthContext';
import { getApiUrl } from '@/lib/utils';
import { useGraphStore } from '@/stores/graphStore';
import { useStoryStore } from '../../stores/storyStore'; // Correct relative import
import dagre from 'dagre';
import StoryNode from '@/components/graph/StoryNode';

// Dummy initial nodes and edges for ReactFlow
const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

const nodeTypes = { storyNode: StoryNode };

const API_URL = getApiUrl();

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 172;
const nodeHeight = 36;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? Position.Left : Position.Top;
    node.sourcePosition = isHorizontal ? Position.Right : Position.Bottom;

    // We are shifting the dagre node position (anchor=center center) to the top left
    // so it matches the React Flow node anchor point (top left).
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };

    return node;
  });

  return { nodes: layoutedNodes, edges };
};

const TemporalMap = ({ volumeId }: { volumeId: string }) => {
  const { user, session } = useAuth();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [volume, setVolume] = useState<any>(null); // State to hold volume data
  
  const setCurrentNode = useStoryStore((state) => state.setCurrentNode);

  const fetchGraph = useGraphStore((state) => state.fetchGraph);
  const addNodeToStore = useGraphStore((state) => state.addNode);

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setCurrentNode(node.id);
  }, [setCurrentNode]);

  useEffect(() => {
    if (!user?.id || !session || !volumeId) return;

    const loadGraph = async () => {
      try {
        const token = session.access_token;
        const headers = { Authorization: `Bearer ${token}` };

        // Fetch volume details to get status
        const volumeResponse = await axios.get(`${API_URL}/api/v1/volumes/${volumeId}`, { headers });
        setVolume(volumeResponse.data);

        // Fetch nodes
        const nodesResponse = await axios.get(`${API_URL}/api/v1/volumes/${volumeId}/nodes`, { headers });
        const fetchedNodes: Node[] = nodesResponse.data.map((dbNode: any) => ({
          id: dbNode.id,
          position: { x: 0, y: 0 }, // Position will be set by layout
          data: { 
            title: dbNode.title, 
            summary: dbNode.content?.summary, 
            type: dbNode.type, 
            novelty_score: dbNode.content?.novelty_score,
            volume_id: dbNode.volume_id,
            branch_id: dbNode.branch_id,
          },
          type: 'storyNode', // Use our custom StoryNode type
        }));

        // Fetch edges
        const edgesResponse = await axios.get(`${API_URL}/api/v1/volumes/${volumeId}/edges`, { headers });
        const fetchedEdges: Edge[] = edgesResponse.data.map((dbEdge: any) => ({
          id: dbEdge.id,
          source: dbEdge.source_node_id,
          target: dbEdge.target_node_id,
          label: dbEdge.label || dbEdge.type,
          type: 'default', // Using default for now
        }));

        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
          fetchedNodes,
          fetchedEdges
        );

        setNodes(layoutedNodes);
        setEdges(layoutedEdges);

        // Populate Zustand store
        await fetchGraph(volumeId, token);

      } catch (error) {
        console.error('Failed to fetch graph data:', error);
      }
    };

    loadGraph();
  }, [user, session, volumeId, fetchGraph, setNodes, setEdges]); // Added setNodes and setEdges to deps

  const handleWriteManuscript = async () => {
    if (!volumeId || !session) return;
    try {
        await axios.post(`${API_URL}/api/v1/volumes/${volumeId}/write`, {}, {
            headers: { Authorization: `Bearer ${session.access_token}` }
        });
        // Optionally, refetch volume data to update status
        alert('Manuscript writing has been initiated!');
    } catch (error) {
        console.error('Failed to start manuscript writing:', error);
        alert('Failed to start manuscript writing.');
    }
  };

  const handleGenerateIllustrations = async () => {
    if (!volumeId || !session) return;
    try {
        await axios.post(`${API_URL}/api/v1/volumes/${volumeId}/illustrate`, {}, {
            headers: { Authorization: `Bearer ${session.access_token}` }
        });
        alert('Illustration generation has been initiated!');
    } catch (error) {
        console.error('Failed to start illustration generation:', error);
        alert('Failed to start illustration generation.');
    }
  };

  const addRandomNode = useCallback(() => {
    const newNodeId = `node-${nodes.length + 1}`;
    const newNode: Node = {
      id: newNodeId,
      position: { x: Math.random() * 250, y: Math.random() * 250 },
      data: { label: `New Node ${nodes.length + 1}`, summary: 'A dynamically added node.' },
      type: 'default',
    };
    
    // Simple logic to connect new node to the last node for testing layout
    const newEdge: Edge = {
        id: `edge-${nodes.length}`,
        source: nodes.length > 0 ? nodes[nodes.length - 1].id : 'node-root', 
        target: newNodeId
    };

    const newNodes = nodes.concat(newNode);
    const newEdges = edges.concat(nodes.length > 0 ? [newEdge] : []);
    
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        newNodes,
        newEdges
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    if (session) {
      addNodeToStore({ // Example of adding to Zustand store (needs real data)
          id: newNode.id, 
          volume_id: volumeId, 
          branch_id: 'main', // Assuming 'main' for now
          title: newNode.data.label, 
          type: newNode.type || 'narrative_beat', 
          content: { summary: newNode.data.summary },
          context_snapshot: '',
      }, session.access_token);
    }
  }, [nodes, edges, setNodes, setEdges, addNodeToStore, volumeId, session]);

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
      >
        <MiniMap />
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        <Panel position="top-right" className="space-x-2">
            {volume && (volume.status === 'drafting' || volume.status === 'architected') && (
                <button onClick={handleWriteManuscript} className="p-2 bg-green-600 text-white rounded">Write Manuscript</button>
            )}
            {volume && volume.status === 'text_ready' && (
                <button onClick={handleGenerateIllustrations} className="p-2 bg-purple-600 text-white rounded">Generate Illustrations</button>
            )}
            <button onClick={addRandomNode} className="p-2 bg-blue-500 text-white rounded">Add Node</button>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default TemporalMap;
