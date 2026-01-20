import Link from 'next/link';
import { BookOpen, Clock, Layers } from 'lucide-react';

interface VolumeSummary {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

interface Storyline {
  id: string;
  name: string;
  summary: string;
  volumes: VolumeSummary[];
  created_at: string;
}

interface StorylineCardProps {
  storyline: Storyline;
}

export default function StorylineCard({ storyline }: StorylineCardProps) {
  const volumeCount = storyline.volumes.length;
  const completedCount = storyline.volumes.filter(v => v.status === 'text_ready' || v.status === 'published' || v.status === 'completed').length;
  const progress = volumeCount > 0 ? (completedCount / volumeCount) * 100 : 0;

  // Determine status color
  let statusColor = 'bg-gray-600';
  if (progress === 100) statusColor = 'bg-emerald-500';
  else if (progress > 0) statusColor = 'bg-yellow-500';

  return (
    <div className="group p-5 bg-slate-900 rounded-xl border border-slate-800 hover:border-purple-500 transition-all relative overflow-hidden flex flex-col justify-between shadow-lg h-full">
      
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">Saga</span>
          </div>
          <h3 className="text-lg font-bold text-slate-100 group-hover:text-white truncate max-w-[200px]">
            {storyline.name}
          </h3>
        </div>
        <span className="text-xs text-slate-500 flex items-center gap-1">
           <Clock size={12} /> {new Date(storyline.created_at).toLocaleDateString()}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>{completedCount}/{volumeCount} Epochs Ready</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div 
            className={`h-full ${statusColor} transition-all duration-500`} 
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      {/* Volume Preview List (Mini) */}
      <div className="flex-1 space-y-2 mb-4 overflow-hidden">
        {storyline.volumes.slice(0, 3).map((vol) => (
          <div key={vol.id} className="flex items-center gap-2 text-xs text-slate-400">
            <span className={`w-1.5 h-1.5 rounded-full ${vol.status.includes('ready') || vol.status === 'completed' ? 'bg-emerald-500' : 'bg-slate-600'}`}></span>
            <span className="truncate">{vol.title}</span>
          </div>
        ))}
        {volumeCount > 3 && (
            <div className="text-xs text-slate-600 italic">+ {volumeCount - 3} more...</div>
        )}
      </div>

      {/* Action */}
      <div className="pt-4 border-t border-slate-800">
        <Link href={`/storyline/${storyline.id}`} passHref>
          <button className="w-full py-2 px-3 text-sm font-bold rounded-md bg-purple-600 hover:bg-purple-500 text-white transition flex items-center justify-center gap-2 shadow-lg shadow-purple-900/20">
            <BookOpen size={16} />
            Enter Saga
          </button>
        </Link>
      </div>
    </div>
  );
}
