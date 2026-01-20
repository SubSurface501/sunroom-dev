import React from 'react';
import { useStoryStore } from '../../stores/storyStore';

export const NodeDetailsPanel = () => {
  const selectedNodeId = useStoryStore((state) => state.currentNodeId);
  const expandNode = useStoryStore((state) => state.expandNode);
  const ghostOptions = useStoryStore((state) => state.ghostOptions);
  const isExpanding = useStoryStore((state) => state.isExpanding);
  const clearGhosts = useStoryStore((state) => state.clearGhosts);
  const materializeGhost = useStoryStore((state) => state.materializeGhost);

  const selectedNode = React.useMemo(() => selectedNodeId ? { id: selectedNodeId, data: { label: selectedNodeId, summary: "" } } : null, [selectedNodeId]);

  if (!selectedNode) return <div className="p-4">Select a node to view details.</div>;

  const handleExpand = () => {
    // assuming 'main' branch for MVP, or grab from store
    // Need to ensure activeVolumeId is available in the store
    expandNode(selectedNode.id, 'main'); 
  };

  const handleMaterialize = async (option: any) => { // Use any for now, as GhostOption is not directly imported
    if (!selectedNode) return;
    
    // Call the store action
    await materializeGhost(selectedNode.id, option);
    
    // Optional: Add a toast notification here
    console.log("Node created!");
  };

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white p-4 border-l border-gray-700 overflow-y-auto">
      
      {/* --- Existing Node Info --- */}
      <h2 className="text-xl font-bold mb-2">{selectedNode.data.label}</h2>
      <div className="text-gray-300 text-sm mb-6">
        {selectedNode.data.summary || "No summary available."}
      </div>

      {/* --- The Sprawl Interface --- */}
      <div className="border-t border-gray-700 pt-4 mt-auto">
        <h3 className="text-sm font-semibold text-purple-400 uppercase tracking-wider mb-3">
          Narrative Sprawl
        </h3>

        {/* The Expand Button */}
        <button
          onClick={handleExpand}
          disabled={isExpanding}
          className={`w-full py-2 px-4 rounded font-medium transition-colors ${
            isExpanding 
              ? 'bg-purple-900 text-purple-300 cursor-not-allowed'
              : 'bg-purple-600 hover:bg-purple-500 text-white'
          }`}
        >
          {isExpanding ? 'Consulting Architect...' : 'Expand Frontier'}
        </button>

        {/* The Ghost Nodes List */}
        {ghostOptions.length > 0 && (
          <div className="mt-4 space-y-3 animate-fade-in">
            <p className="text-xs text-gray-500">Select a path to materialize:</p>
            
            {ghostOptions.map((option, idx) => (
              <div 
                key={idx}
                onClick={() => handleMaterialize(option)}
                className="p-3 bg-gray-800 border border-gray-600 rounded cursor-pointer hover:border-purple-400 hover:bg-gray-750 transition-all group"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-sm text-gray-200">{option.title}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-400 group-hover:bg-purple-900 group-hover:text-purple-200">
                    {option.type}
                  </span>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed">
                  {option.summary}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default NodeDetailsPanel;
