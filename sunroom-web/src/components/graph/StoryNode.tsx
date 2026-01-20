import React, { memo, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface StoryNodeData {
  title: string;
  summary: string;
  type: string; // e.g., 'root', 'branch', 'bottleneck'
  novelty_score?: number;
  volume_id: string;
  branch_id: string;
  // Add any other data you want to display
}

const StoryNode: React.FC<NodeProps<StoryNodeData>> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'root':
        return 'border-green-500 bg-green-100';
      case 'bottleneck':
        return 'border-purple-500 bg-purple-100';
      case 'branch':
        return 'border-blue-500 bg-blue-100';
      default:
        return 'border-gray-400 bg-gray-100';
    }
  };

  const getNoveltyColor = (score?: number) => {
    if (score === undefined) return 'bg-gray-400';
    if (score > 0.8) return 'bg-green-500';
    if (score > 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div
      className={`px-4 py-2 shadow-md rounded-md border-2 ${getNodeColor(data.type)}`}
      onClick={toggleExpanded}
    >
      <Handle type="target" position={Position.Top} className="-top-2 !bg-teal-500" />
      <div className="flex flex-col">
        <div className="flex justify-between items-center">
          <div className="flex-1 min-w-0 text-lg font-bold text-gray-800" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{data.title}</div>
          {/* {data.novelty_score !== undefined && (
            <span
              className={`text-xs text-white px-2 py-0.5 rounded-full ${getNoveltyColor(data.novelty_score)}`}
            >
              {data.novelty_score.toFixed(2)}
            </span>
          )} */}
        </div>
        <div
          className={`text-gray-600 text-sm mt-1 ${!isExpanded ? 'overflow-hidden text-ellipsis' : ''}`}
          style={{ whiteSpace: isExpanded ? 'pre-wrap' : 'nowrap', wordBreak: 'break-word' }}
        >
          {data.summary || 'No summary'}
        </div>
        <div className="text-gray-500 text-xs mt-1">Type: {data.type}</div>
        {/* Add more info or controls here */}
      </div>
      <Handle type="source" position={Position.Bottom} className="-bottom-2 !bg-blue-500" />
    </div>
  );
};

export default memo(StoryNode);
