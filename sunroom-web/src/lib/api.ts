import axios from 'axios';
import { Category } from '@/types/schema'; // Import Category schema

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = {
  // 1. Ingestion
  uploadFile: async (file: File, token: string, onUploadProgress: (progressEvent: any) => void, manualLens?: string, categoryId?: string, universeId?: string, discoveryEpochId?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    if (manualLens) formData.append('manual_lens_name', manualLens);
    if (categoryId) formData.append('category_id', categoryId); 
    if (universeId) formData.append('universe_id', universeId);
    if (discoveryEpochId) formData.append('discovery_epoch_id', discoveryEpochId.toString());
    
    const res = await axios.post(`${API_URL}/api/v1/sources`, formData, {
      headers: { 
        'Content-Type': 'multipart/form-form-data',
        'Authorization': `Bearer ${token}`
      },
      onUploadProgress
    });
    return res.data;
  },

  // Categories CRUD
  getStaticCategories: async (token: string): Promise<Category[]> => {
    const res = await axios.get(`${API_URL}/api/v1/categories`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return res.data;
  },

  // 2. Synthesis (FIXED: Maps to Backend 'GenerateVolumeRequest')
  triggerSynthesis: async (token: string, projectId: string, prompt: string, lens: string = 'General') => {
    // We map 'prompt' -> 'topic' because api_server.py expects 'topic'
    const res = await axios.post(`${API_URL}/api/v1/volumes/generate`, {
      project_id: projectId,
      topic: prompt,     // Backend expects 'topic'
      lenses: [lens],    // Backend expects List[str]
      seed_prose: "",    // Optional
      depth: 6           // Default depth
    }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    // Returns { volume_id: "...", task_id: "..." }
    return res.data;
  },

  // 3. Status Check (FIXED: Now points to the new polling endpoint)
  checkTaskStatus: async (token: string, taskId: string) => {
    const res = await axios.get(`${API_URL}/api/v1/tasks/${taskId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    // Returns { status: "PENDING" | "SUCCESS" | "FAILURE", result: ... }
    return res.data;
  },
  
  // 4. List Volumes (FIXED: Removed /synthesis prefix)
  getVolumes: async (token: string, projectId: string) => {
      // The backend endpoint is just /api/v1/volumes (it filters by user_id inside the token)
      const res = await axios.get(`${API_URL}/api/v1/volumes`, {
          headers: { 'Authorization': `Bearer ${token}` }
      });
      return res.data;
  }
};