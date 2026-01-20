'use client';
import { useState, useEffect } from 'react';
import { Upload, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { supabase } from '@/lib/supabase';
import { Category } from '@/types/schema';

export default function UploadZone({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | undefined>(undefined);

  useEffect(() => {
    const fetchData = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      try {
        const fetchedCategories = await api.getStaticCategories(session.access_token);
        setCategories(fetchedCategories);
      } catch (error) {
        console.error("Failed to fetch categories:", error);
      }
    };
    fetchData();
  }, []);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) return;

    try {
      for (const file of Array.from(files)) {
        // Simple upload to PKG. No universe or epoch required here.
        await api.uploadFile(file, session.access_token, () => {}, undefined, selectedCategoryId);
      }
      onUploadComplete();
    } catch (e) {
      console.error("Upload failed", e);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div 
      className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors bg-gray-900/50
        ${isDragging ? 'border-purple-500 bg-purple-500/10' : 'border-gray-700'}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleUpload(e.dataTransfer.files);
      }}
    >
      <div className="flex flex-col items-center gap-3">
        <Upload className={`w-8 h-8 ${isUploading ? 'animate-bounce text-yellow-500' : 'text-gray-500'}`} />
        <h3 className="text-sm font-medium text-gray-200">Drop Source Material</h3>
        <p className="text-[10px] text-gray-500">Files will be processed into your PKG</p>
        
        <select
          className="w-full mt-2 p-1 rounded bg-gray-800 border border-gray-700 text-xs text-white outline-none focus:border-purple-500"
          value={selectedCategoryId || ''}
          onChange={(e) => setSelectedCategoryId(e.target.value || undefined)}
          disabled={isUploading}
        >
          <option value="">Ungrouped</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>

        <label className={`mt-2 px-4 py-2 rounded text-xs font-bold uppercase cursor-pointer transition-all 
          ${isUploading ? 'bg-gray-800 text-gray-500' : 'bg-purple-600 text-white hover:bg-purple-500'}`}>
          {isUploading ? <Loader2 size={14} className="animate-spin" /> : 'Select Files'}
          <input type="file" multiple className="hidden" onChange={(e) => handleUpload(e.target.files)} disabled={isUploading} />
        </label>
      </div>
    </div>
  );
}