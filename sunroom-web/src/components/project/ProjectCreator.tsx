import React, { useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useWorkspace } from '@/context/WorkspaceContext';

interface ProjectCreatorProps {
  onProjectCreated: (projectId: string) => void;
  onCancel: () => void;
}

export default function ProjectCreator({ onProjectCreated, onCancel }: ProjectCreatorProps) {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const { setWorkspace } = useWorkspace();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const { data: { session } } = await supabase.auth.getSession();
      
      const res = await fetch(`${apiUrl}/api/v1/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({ name: name })
      });

      if (!res.ok) throw new Error('Failed to create project');

      const project = await res.json();
      
      // Auto-switch to the new project context
      setWorkspace('project', project.id, project.name);
      onProjectCreated(project.id);
      
    } catch (err) {
      console.error(err);
      alert('Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl">
      <h3 className="text-lg font-bold text-white mb-4">Create New Project</h3>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-1">Project Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Project Genesis"
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white focus:ring-2 focus:ring-blue-500 outline-none"
            autoFocus
          />
        </div>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-400 hover:text-white text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-bold text-sm disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  );
}
