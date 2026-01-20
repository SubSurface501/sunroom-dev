'use client';
import { useParams } from 'next/navigation';
import UploadZone from '@/components/UploadZone';
import SunRoom from '@/components/SunRoom';

export default function ProjectWorkspace() {
  const params = useParams();
  const projectId = params.id as string;

  return (
    <div className="h-screen bg-gradient-to-br from-slate-100 to-slate-200 p-6 flex gap-6">
      
      {/* Left Column: Source Material (The Archive) */}
      <div className="w-1/3 flex flex-col gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border h-full overflow-y-auto">
          <h2 className="text-xl font-bold mb-4 text-gray-800">Source Material</h2>
          <UploadZone onUploadComplete={() => {}} />
          
          <div className="mt-8">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Knowledge Graph</h3>
            {/* List ingested atoms/files here later */}
            <div className="text-sm text-gray-400 italic">No atoms visible (MVP)</div>
          </div>
        </div>
      </div>

      {/* Right Column: The Room (Synthesis) */}
      <div className="w-2/3">
        <SunRoom projectId={projectId} />
      </div>
    </div>
  );
}
