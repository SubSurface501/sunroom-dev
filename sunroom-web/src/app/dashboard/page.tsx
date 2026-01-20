'use client';

import React, { useState, useEffect, useMemo, useCallback, Suspense } from 'react';
import axios from 'axios';
import { getApiUrl } from '@/lib/utils';
import { StoryVolume, Source } from '@/types/schema';
import { useAuth } from '@/components/AuthContext';
import { SourceInspector } from '@/components/SourceInspector'; 
import UploadZone from '@/components/UploadZone';
import ProjectCard from '@/components/ProjectCard'; 
import StorylineCard from '@/components/StorylineCard';
import { CreateVolumeModal } from '@/components/CreateVolumeModal';
import { BillingButton } from '@/components/Billing/BillingButton';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { CategoryManagerModal } from '@/components/CategoryManagerModal'; // Import CategoryManagerModal
import { FolderKanban } from 'lucide-react'; // Import an icon for category management

const API_URL = getApiUrl();

function DashboardPageContent() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false); // New state for category modal
  const [highlightedVolumeId, setHighlightedVolumeId] = useState<string | null>(null);
  
  // State for StoryVolumes & Storylines
  const [volumes, setVolumes] = useState<StoryVolume[]>([]);
  const [storylines, setStorylines] = useState<any[]>([]);
  
  // State for Sources (lifted from SourceInspector)
  const [sources, setSources] = useState<Source[]>([]);
  const [groupedSources, setGroupedSources] = useState<Map<string, Source[]>>(new Map());
  const [sourcesLoading, setSourcesLoading] = useState(false);

  const { user, session } = useAuth();
  const searchParams = useSearchParams();

  // Effect to read highlightVolumeId from URL and set temporary highlight
  useEffect(() => {
    const volumeIdFromQuery = searchParams.get('highlightVolumeId');
    if (volumeIdFromQuery) { 
      setHighlightedVolumeId(volumeIdFromQuery);
      const timer = setTimeout(() => {
        setHighlightedVolumeId(null); // Clear highlight after 5 seconds
      }, 5000); 
      return () => clearTimeout(timer); 
    }
  }, [searchParams]);

  // --- Data Fetching for Sources ---
  const fetchSources = useCallback(async (isInitialLoad = false) => {
    if (!user || !session) return false;
    if (isInitialLoad) setSourcesLoading(true);
    try {
      const token = session.access_token;
      const response = await axios.get(`${API_URL}/api/v1/sources`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const fetchedSources: Source[] = response.data;

      const isStillProcessing = fetchedSources.some(s => s.processing_status && s.processing_status !== 'completed' && s.processing_status !== 'failed');

      const groups = new Map<string, Source[]>();
      fetchedSources.forEach(source => {
        const categoryName = source.category_name || 'Ungrouped'; // Group by category_name
        if (!groups.has(categoryName)) {
          groups.set(categoryName, []);
        }
        groups.get(categoryName)?.push(source);
      });
      setGroupedSources(groups);
      setSources(fetchedSources);

      return isStillProcessing;
    } catch (error) {
      console.error("Failed to fetch sources:", error);
      return false;
    } finally {
      if (isInitialLoad) setSourcesLoading(false);
    }
  }, [user, session]); // useCallback dependencies

  // --- Data Fetching for Volumes ---
  const fetchVolumes = useCallback(async () => {
    if (!user || !session) return;
    try {
        const token = session.access_token;
        const response = await axios.get(`${API_URL}/api/v1/volumes`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        setVolumes(response.data);
    } catch (error) {
        console.error("Failed to fetch volumes:", error);
    }
  }, [user, session]);

  // --- Data Fetching for Storylines ---
  const fetchStorylines = useCallback(async () => {
    if (!user || !session) return;
    try {
        const token = session.access_token;
        const response = await axios.get(`${API_URL}/api/v1/storylines/dashboard`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        setStorylines(response.data);
    } catch (error) {
        console.error("Failed to fetch storylines:", error);
    }
  }, [user, session]);

  // Initial data fetch and polling setup
  useEffect(() => {
    // Do not run any fetches until the session is ready
    if (!session) {
      return;
    }

    const fetchData = () => {
        fetchVolumes();
        fetchStorylines();
        fetchSources();
    };

    // Perform the initial fetch immediately now that we know we have a session
    fetchData();

    // Set up a single, simple interval for polling
    const intervalId = setInterval(fetchData, 3000); // Poll every 3 seconds

    // Cleanup function to clear the interval when the component unmounts
    return () => clearInterval(intervalId);
  }, [session, fetchVolumes, fetchStorylines, fetchSources]); // Now depends on session to re-trigger if it changes

  // Filter volumes to exclude those that belong to a storyline (orphan logic)
  const orphanVolumes = useMemo(() => 
    volumes.filter(vol => !vol.storyline_id),
    [volumes]
  );

  const activeManuscripts = useMemo(() => 
    orphanVolumes.filter(vol => ["architecting", "drafting", "writing"].includes(vol.status)), 
    [orphanVolumes]
  );
  
  const completedStorybooks = useMemo(() => 
    orphanVolumes.filter(vol => !["architecting", "drafting", "writing"].includes(vol.status)), 
    [orphanVolumes]
  );

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden font-sans">
      {/* Left Col: Sources (Data Ingestion) */}
      <div className="w-80 border-r border-gray-800 bg-gray-900 p-4 flex flex-col h-full">
        <h2 className="text-lg font-bold text-purple-400 mb-4 shrink-0">Signal Input</h2>
        <div className="flex flex-col gap-4 flex-1 overflow-y-auto custom-scrollbar">
            <UploadZone onUploadComplete={() => fetchSources(false)} />
            <SourceInspector 
              sources={sources} 
              groupedSources={groupedSources} 
              loading={sourcesLoading} 
              onDeleteSource={() => fetchSources(false)}
            />
        </div>
      </div>

      {/* Center Col: The Radar (Insight & Projects) */}
      <div className="flex-1 p-8 overflow-y-auto custom-scrollbar">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight">The Radar</h1>
          
          <div className="flex items-center space-x-4">
            <BillingButton />
            <Link href="/knowledge-graph" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium shadow-lg transition-all">
              Knowledge Graph
            </Link>
            <button 
              onClick={() => setIsCategoryModalOpen(true)} // Open category modal
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md font-medium shadow-lg transition-all flex items-center gap-2"
            >
              <FolderKanban size={18} /> Manage Categories
            </button>
            <button 
              onClick={() => setIsModalOpen(true)}
              className="bg-purple-600 hover:bg-purple-500 text-white px-6 py-2 rounded-md font-medium shadow-lg transition-all"
            >
              + New Operation
            </button>
          </div>
        </div>

        {/* NEW: Active Sagas Section */}
        {storylines.length > 0 && (
          <section className="mb-12">
            <h3 className="text-sm uppercase text-gray-500 tracking-wider mb-4">Active Sagas</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {storylines.map((sl) => (
                    <StorylineCard key={sl.id} storyline={sl} />
                ))}
            </div>
          </section>
        )}

        {/* Active Manuscripts Section */}
        <section className="mb-12">
          <h3 className="text-sm uppercase text-gray-500 tracking-wider mb-4">Active Manuscripts (Standalone)</h3>
           <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {activeManuscripts.length > 0 ? (
                    activeManuscripts.map((vol) => (
                        <ProjectCard key={vol.id} volume={vol} isHighlighted={vol.id === highlightedVolumeId} />
                    ))
                ) : (
                    <p className="text-gray-500 italic">No active manuscripts in progress.</p>
                )}
            </div>
        </section>

        {/* Completed Storybooks Section */}
        <section>
          <h3 className="text-sm uppercase text-gray-500 tracking-wider mb-4">Completed Storybooks</h3>
           <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {completedStorybooks.length > 0 ? (
                    completedStorybooks.map((vol) => (
                        <ProjectCard key={vol.id} volume={vol} isHighlighted={vol.id === highlightedVolumeId} />
                    ))
                ) : (
                    <p className="text-gray-500 italic">No completed storybooks yet.</p>
                )}
            </div>
        </section>
      </div>

      {/* The Architect Modal */}
      {isModalOpen && <CreateVolumeModal onClose={() => setIsModalOpen(false)} />}
      {/* Category Manager Modal */}
      {isCategoryModalOpen && <CategoryManagerModal 
        onClose={() => setIsCategoryModalOpen(false)} 
        onCategoriesUpdated={() => fetchSources(false)} // Refresh sources if categories change
      />}
    </div>
  );
};

export default function DashboardPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <DashboardPageContent />
    </Suspense>
  );
}