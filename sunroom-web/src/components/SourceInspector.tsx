'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getApiUrl } from '@/lib/utils';
import { useAuth } from './AuthContext';
import { FileAudio, FileText, Image as ImageIcon, Video, Loader2, ChevronDown, ChevronRight, CheckCircle, AlertTriangle, Trash2 } from 'lucide-react';

const API_URL = getApiUrl();

import { Source } from '@/types/schema';

interface SourceInspectorProps {
  sources: Source[];
  groupedSources: Map<string, Source[]>;
  loading: boolean;
  onDeleteSource: () => void;
}

// Helper to determine progress percentage
const getProgress = (status?: string): number => {
  switch (status) {
    case 'processing': return 10;
    case 'downloading': return 20;
    case 'transcribing': return 50;
    case 'diarizing': return 80;
    case 'indexing': return 95;
    case 'completed': return 100;
    default: return 0;
  }
};

export const SourceInspector = ({ sources, groupedSources, loading, onDeleteSource }: SourceInspectorProps) => {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const { session } = useAuth();

  // Inside SourceInspector.tsx, replace the existing useEffect with this:

  useEffect(() => {
    // Only auto-expand categories that have ACTIVE processing
    // but DO NOT collapse categories the user has manually opened.
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      sources.forEach(source => {
        const isProcessing = source.processing_status && 
                             source.processing_status !== 'completed' && 
                             source.processing_status !== 'failed';
        if (isProcessing) {
          newSet.add(source.category_name || 'Ungrouped');
        }
      });
      return newSet;
    });
  }, [sources]); 
  // By returning a merged set, your manual 'Ungrouped' click stays open.

  const handleDeleteSource = async (sourceId: string) => {
    if (!session) return;
    if (window.confirm("Are you sure you want to permanently delete this source? This action cannot be undone.")) {
      try {
        const token = session.access_token;
        await axios.delete(`${API_URL}/api/v1/sources/${sourceId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        onDeleteSource();
      } catch (error) {
        console.error("Failed to delete source:", error);
        alert("Failed to delete source. Please try again.");
      }
    }
  };

  const toggleCategoryExpansion = (categoryName: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(categoryName)) {
        newSet.delete(categoryName);
      } else {
        newSet.add(categoryName);
      }
      return newSet;
    });
  };

  const getIcon = (type: string) => {
    switch(type) {
      case 'audio': return <FileAudio size={16} className="text-purple-400" />;
      case 'video': return <Video size={16} className="text-pink-400" />;
      case 'image': return <ImageIcon size={16} className="text-cyan-400" />;
      default: return <FileText size={16} className="text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center p-4">
        <Loader2 className="animate-spin text-purple-500" />
      </div>
    );
  }

  if (sources.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-8">
        No signals detected.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {[...groupedSources.keys()].map(categoryName => (
        <div key={categoryName} className="bg-gray-800/60 rounded-lg border border-gray-700">
          <button
            className="flex items-center justify-between w-full p-3 text-left hover:bg-gray-700/50 transition-colors rounded-t-lg"
            onClick={() => toggleCategoryExpansion(categoryName)}
          >
            <h3 className="text-sm font-semibold text-gray-200">
              {categoryName} ({groupedSources.get(categoryName)?.length || 0})
            </h3>
            {expandedCategories.has(categoryName) ? (
              <ChevronDown size={16} className="text-gray-400" />
            ) : (
              <ChevronRight size={16} className="text-gray-400" />
            )}
          </button>
          {expandedCategories.has(categoryName) && (
            <div className="border-t border-gray-700 p-2 space-y-1">
              {groupedSources.get(categoryName)?.map((source) => {
                const status = source.processing_status || (source.is_processed ? 'completed' : 'processing');
                const isProcessing = status !== 'completed' && status !== 'failed';
                const progress = getProgress(status);

                return (
                  <div 
                    key={source.id} 
                    className="flex items-center gap-3 p-2 bg-gray-800/40 rounded-lg group"
                  >
                    <div className="shrink-0">
                      {isProcessing ? <Loader2 size={16} className="animate-spin text-yellow-400" /> : getIcon(source.source_type)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="text-sm font-medium text-gray-300 truncate group-hover:text-white transition-colors">
                        {source.title}
                      </h4>
                      {isProcessing ? (
                        <div className="mt-1">
                          <div className="flex justify-between items-center text-xs text-yellow-400 mb-0.5">
                            <span className="capitalize">{status}...</span>
                            <span>{source.estimated_processing_time_minutes} min est.</span>
                          </div>
                          <div className="w-full bg-gray-600 rounded-full h-1">
                            <div className="bg-yellow-500 h-1 rounded-full" style={{ width: `${progress}%` }}></div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 mt-0.5">
                          {status === 'completed' && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-900/30 text-green-400 flex items-center gap-1">
                              <CheckCircle size={10} /> Processed
                            </span>
                          )}
                          {status === 'failed' && (
                             <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-900/30 text-red-400 flex items-center gap-1">
                              <AlertTriangle size={10} /> Failed
                            </span>
                          )}
                          <span className="text-[10px] text-gray-600">
                            {new Date(source.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                    <button 
                      onClick={() => handleDeleteSource(source.id)}
                      className="ml-2 p-1 rounded-full text-gray-500 hover:bg-red-900/50 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Delete Source"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
