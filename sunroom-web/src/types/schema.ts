export type NodeRole = 'root' | 'branch' | 'bottleneck' | 'ending';

export interface GraphNode {
  node_id: string;
  type: NodeRole;
  title: string;
  content: {
    summary: string;
    novelty_score?: number;
    feedback?: string;
  };
  novelty_score?: number; // Keep for legacy blueprint page use
}

export interface GraphConnection {
  from: string;
  to: string;
  choice_label: string;
  joint_type?: string;
}

export interface StoryVolume {
  id: string;
  title: string;
  root_concept: string;
  status: string;
  graph_structure?: {
    nodes: GraphNode[];
    connections: GraphConnection[];
  };
  master_asset_bank?: Record<string, string>;
  created_at: string;
  storyline_id?: string;
}

export interface TrailheadPage {
  page_number: number;
  narrative_text: string;
  visual_prompt?: string;
  image_url?: string;
}

export interface TrailheadContent {
  summary: string;
  research_dossier?: any[];
  pages: TrailheadPage[];
}

export interface Trailhead {
  id: string;
  title: string;
  content: TrailheadContent;
  status: string;
}

export interface Source {
  id: string;
  user_id: string;
  title: string;
  storage_path: string;
  metadata: Record<string, any>;
  created_at: string;
  is_processed: boolean;
  media_duration_seconds?: number;
  source_type: 'audio' | 'video' | 'document' | 'image' | 'manual' | 'youtube_transcript' | 'personal_journal' | 'uploaded_text' | 'web_scrape' | 'youtube_video';
  original_publication_date?: string;
  date_confidence?: number;
  author?: string;
  category_id?: string;
  category_name?: string;
  processing_status?: 'processing' | 'downloading' | 'transcribing' | 'diarizing' | 'indexing' | 'completed' | 'failed';
  estimated_processing_time_minutes?: number;
}

export interface Category {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}
