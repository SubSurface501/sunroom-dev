import axios from 'axios';
import { supabase } from '@/lib/supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create an axios instance with interceptors
const apiClient = axios.create({
  baseURL: API_URL,
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(async (config) => {
  // Use the Supabase client to get the session securely
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  if (token) {
      config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
});

export const api = {
  // Generic Wrappers
  get: (url: string, config = {}) => apiClient.get(url, config),
  post: (url: string, data = {}, config = {}) => apiClient.post(url, data, config),

  // 1. Standard (System 1)
  generateFast: async (prompt: string) => {
    // This would match your existing basic generation if you have one
    return apiClient.post(`/api/v1/thoughts/fast`, { prompt }); 
  },

  // 2. Deep (System 2 / Constrained)
  startDeepThought: async (prompt: string, volumeId: string) => {
    return apiClient.post(`/api/v1/thoughts/constrained`, { 
      prompt, 
      volume_id: volumeId 
    });
  },

  // 3. Poll Task Status (For Deep Thinking)
  getTaskStatus: async (taskId: string) => {
    return apiClient.get(`/api/v1/tasks/${taskId}`);
  },

  // 4. Collaborative (Composite Mind)
  startCollaboration: async (prompt: string, volumeId: string, collaboratorMap: Record<string, string>) => {
    return apiClient.post(`/api/v1/collaboration/braid`, {
      prompt,
      volume_id: volumeId,
      collaborator_map: collaboratorMap
    });
  },

  // 5. Curator (The Refinery)
  triggerCuratorScan: async (coreThemes: string, volumeId?: string) => {
    return apiClient.post(`/api/v1/curator/scan`, { core_themes: coreThemes, volume_id: volumeId });
  },
  
  getTrailheads: async () => {
    return apiClient.get(`/api/v1/trailheads`);
  },

  // 6. Ingestion
  ingestSource: async (formData: FormData) => {
    return apiClient.post(`/api/v1/sources`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
            // Auth header added by interceptor automatically
        }
    });
  }
};
