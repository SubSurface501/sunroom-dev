import React from 'react';
import { Upload } from 'lucide-react';

interface EmptyStateProps {
  onIngest: () => void;
}

export default function EmptyState({ onIngest }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-100px)] text-center p-8">
      <div className="w-24 h-24 bg-gray-800 rounded-full flex items-center justify-center mb-6 animate-pulse">
        <span className="text-4xl">☀</span>
      </div>
      <h1 className="text-3xl font-light text-white mb-2">Your Sun Room is Empty</h1>
      <p className="text-gray-400 max-w-md mb-8">
        To begin, we need to map your mind. Upload your journals, books, or transcripts to crystallize your first Atoms.
      </p>
      
      <div className="flex gap-4">
        <button 
          onClick={onIngest}
          className="flex items-center gap-2 px-6 py-3 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg font-bold transition-all shadow-[0_0_20px_rgba(234,179,8,0.3)]"
        >
          <Upload size={18} />
          Ingest Knowledge
        </button>
        
        {/* Placeholder for Demo Data */}
        {/* <button className="px-6 py-3 border border-gray-700 text-gray-400 hover:text-white rounded-lg">
          Use Demo Data
        </button> */}
      </div>
    </div>
  );
}
