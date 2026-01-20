import { FileText, Clock, AlertCircle, PlayCircle, Image } from 'lucide-react'; // Added PlayCircle and Image
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useState, useEffect } from 'react'; // Added useState and useEffect
import { useAuth } from '@/components/AuthContext'; // Import useAuth
import axios from 'axios'; // Import axios

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'; // Get API URL

interface Volume {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

interface ProjectCardProps {
  volume: Volume;
  isHighlighted?: boolean;
}

export default function ProjectCard({ volume, isHighlighted = false }: ProjectCardProps) {
  const router = useRouter();
  const { user, session } = useAuth(); // Get user and session
  const isPlayable = volume.status === 'completed' || volume.status === 'published' || volume.status === 'text_ready';

  const [isAnimating, setIsAnimating] = useState(false);
  const [isIllustrating, setIsIllustrating] = useState(false); // New state for illustration loading

  useEffect(() => {
    if (isHighlighted) {
      setIsAnimating(true);
      const timer = setTimeout(() => {
        setIsAnimating(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [isHighlighted]);

  const handleIllustrate = async () => {
    if (!volume.id || !user || !session) {
      console.error("Missing volumeId, user, or session to illustrate.");
      return;
    }
    setIsIllustrating(true);
    try {
      const token = session.access_token;
      await axios.post(`${API_URL}/api/v1/volumes/${volume.id}/illustrate`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert("Illustration process initiated!"); // Replace with a proper toast/notification
      // Optionally, update volume status to 'illustrating' locally or refetch volumes
    } catch (error) {
      console.error("Failed to initiate illustration:", error);
      alert("Failed to initiate illustration.");
    } finally {
      setIsIllustrating(false);
    }
  };

  return (
    <div
      className={`group p-4 bg-gray-900 rounded-xl border border-gray-800 hover:border-gray-600 transition-all relative overflow-hidden flex flex-col justify-between
      ${isAnimating ? 'ring-4 ring-green-400 ring-opacity-75 animate-pulse' : ''}
      `}
    >
      <div className="flex-grow">
        <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <FileText size={16} className="text-gray-400" />
        </div>

        <h3 className="text-md font-medium text-gray-200 group-hover:text-white truncate pr-6">
          {volume.title || "Untitled Synthesis"}
        </h3>

        <div className="flex items-center gap-2 mt-3 text-xs text-gray-500">
          <span className={`w-2 h-2 rounded-full ${
            volume.status === 'completed' || volume.status === 'published' ? 'bg-green-500' : // Completed/Published
            volume.status === 'drafting' ? 'bg-teal-500' : // Blueprint Ready
            volume.status === 'writing' || volume.status === 'architecting' ? 'bg-yellow-500 animate-pulse' : // In Progress
            'bg-gray-600' // Other/Unknown
          }`} />
          <span className="capitalize">{volume.status.replace('_', ' ')}</span>
          <span className="ml-auto flex items-center gap-1">
              <Clock size={10} />
              {new Date(volume.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-4 flex gap-2 pt-4 border-t border-gray-800">
        <Link href={`/volume/${volume.id}/map`} passHref>
          <button className="flex-1 text-center py-2 px-3 text-xs font-medium rounded-md bg-gray-700 hover:bg-gray-600 text-gray-200 transition">
            View Map
          </button>
        </Link>
        {isPlayable ? (
          <> {/* Use a fragment to group multiple elements */}
            <Link href={`/play/${volume.id}`} passHref>
              <button className="flex-1 text-center py-2 px-3 text-xs font-medium rounded-md bg-blue-600 hover:bg-blue-700 text-white transition flex items-center justify-center gap-1">
                <PlayCircle size={14} /> Play Story
              </button>
            </Link>
            {/* New Illustrate Button */}
            <button
              onClick={handleIllustrate}
              disabled={isIllustrating}
              className="flex-1 text-center py-2 px-3 text-xs font-medium rounded-md bg-orange-600 hover:bg-orange-500 text-white transition flex items-center justify-center gap-1"
            >
              {isIllustrating ? (
                <>
                  <Clock size={14} className="animate-spin" /> Illustrating...
                </>
              ) : (
                <>
                  <Image size={14} /> Illustrate
                </>
              )}
            </button>
          </>
        ) : (
          <>
            <Link href={`/dashboard/blueprint/${volume.id}`} passHref>
              <button className="flex-1 text-center py-2 px-3 text-xs font-medium rounded-md bg-purple-600 hover:bg-purple-500 text-white transition">
                Edit Blueprint
              </button>
            </Link>
            <Link href={`/studio/${volume.id}`} passHref>
              <button className="flex-1 text-center py-2 px-3 text-xs font-medium rounded-md bg-green-600 hover:bg-green-500 text-white transition">
                Edit in Studio
              </button>
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
