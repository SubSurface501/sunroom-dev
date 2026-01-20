'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getApiUrl } from '@/lib/utils';
import { useAuth } from '@/components/AuthContext';
import { X, PlusCircle, Edit, Trash2, Save, XCircle, Loader2 } from 'lucide-react'; // Import icons

const API_URL = getApiUrl();

import { Category } from '@/types/schema';

interface CategoryManagerModalProps {
  onClose: () => void;
  onCategoriesUpdated: () => void; // Callback to refresh categories in parent
}

export const CategoryManagerModal: React.FC<CategoryManagerModalProps> = ({ onClose, onCategoriesUpdated }) => {
  const { session } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryDescription, setNewCategoryDescription] = useState('');
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCategories = async () => {
    if (!session) return;
    setIsLoading(true);
    setError(null);
    try {
      const token = session.access_token;
      const response = await axios.get(`${API_URL}/api/v1/categories`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCategories(response.data);
    } catch (err: any) {
      console.error("Failed to fetch categories:", err);
      setError(`Failed to load categories: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, [session]);

  const handleCreateCategory = async () => {
    if (!session || !newCategoryName.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const token = session.access_token;
      await axios.post(`${API_URL}/api/v1/categories`, { 
        name: newCategoryName, 
        description: newCategoryDescription 
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNewCategoryName('');
      setNewCategoryDescription('');
      fetchCategories(); // Refresh list
      onCategoriesUpdated();
    } catch (err: any) {
      console.error("Failed to create category:", err);
      setError(`Failed to create category: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateCategory = async (categoryId: string) => {
    if (!session || !editingCategory || !editingCategory.name.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const token = session.access_token;
      await axios.patch(`${API_URL}/api/v1/categories/${categoryId}`, { 
        name: editingCategory.name, 
        description: editingCategory.description 
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEditingCategory(null); // Exit editing mode
      fetchCategories(); // Refresh list
      onCategoriesUpdated();
    } catch (err: any) {
      console.error("Failed to update category:", err);
      setError(`Failed to update category: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteCategory = async (categoryId: string) => {
    if (!session) return;
    if (!window.confirm("Are you sure you want to delete this category? Sources assigned to this category will become unassigned.")) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const token = session.access_token;
      await axios.delete(`${API_URL}/api/v1/categories/${categoryId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchCategories(); // Refresh list
      onCategoriesUpdated();
    } catch (err: any) {
      console.error("Failed to delete category:", err);
      setError(`Failed to delete category: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 p-6 rounded-lg shadow-xl w-full max-w-md border border-gray-700">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-white">Manage Categories</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X size={24} />
          </button>
        </div>

        {error && <div className="bg-red-900/30 text-red-400 p-3 rounded-md mb-4 flex items-center gap-2"><XCircle size={20} />{error}</div>}
        {isLoading && <div className="flex items-center gap-2 text-blue-400 mb-4"><Loader2 size={20} className="animate-spin" /> Loading categories...</div>}

        {/* Create New Category */}
        <div className="mb-6 p-4 border border-gray-700 rounded-lg bg-gray-700/30">
          <h3 className="text-lg font-semibold text-white mb-3">Create New Category</h3>
          <input
            type="text"
            placeholder="Category Name"
            className="w-full p-2 mb-2 rounded-md bg-gray-900 border border-gray-600 text-white placeholder-gray-500"
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            disabled={isLoading}
          />
          <textarea
            placeholder="Description (optional)"
            rows={2}
            className="w-full p-2 mb-3 rounded-md bg-gray-900 border border-gray-600 text-white placeholder-gray-500"
            value={newCategoryDescription}
            onChange={(e) => setNewCategoryDescription(e.target.value)}
            disabled={isLoading}
          ></textarea>
          <button 
            onClick={handleCreateCategory}
            className="w-full py-2 bg-purple-600 hover:bg-purple-700 rounded-md text-white flex items-center justify-center gap-2"
            disabled={isLoading || !newCategoryName.trim()}
          >
            <PlusCircle size={20} /> Create Category
          </button>
        </div>

        {/* Existing Categories */}
        <h3 className="text-lg font-semibold text-white mb-3">Existing Categories</h3>
        {categories.length === 0 && !isLoading && !error ? (
          <p className="text-gray-400 text-sm italic">No categories created yet.</p>
        ) : (
          <ul className="space-y-3">
            {categories.map(category => (
              <li key={category.id} className="flex items-center justify-between bg-gray-700/50 p-3 rounded-md border border-gray-700">
                {editingCategory?.id === category.id ? (
                  <div className="flex-1 mr-2">
                    <input
                      type="text"
                      className="w-full p-1 rounded-md bg-gray-900 border border-gray-600 text-white text-sm"
                      value={editingCategory.name}
                      onChange={(e) => setEditingCategory({ ...editingCategory, name: e.target.value })}
                      disabled={isLoading}
                    />
                    <textarea
                      rows={1}
                      className="w-full p-1 mt-1 rounded-md bg-gray-900 border border-gray-600 text-white text-xs"
                      value={editingCategory.description || ''}
                      onChange={(e) => setEditingCategory({ ...editingCategory, description: e.target.value })}
                      disabled={isLoading}
                    ></textarea>
                  </div>
                ) : (
                  <div className="flex-1 mr-2">
                    <h4 className="text-white text-base font-medium">{category.name}</h4>
                    {category.description && <p className="text-gray-400 text-xs mt-1">{category.description}</p>}
                  </div>
                )}
                
                <div className="flex space-x-2">
                  {editingCategory?.id === category.id ? (
                    <>
                      <button 
                        onClick={() => handleUpdateCategory(category.id)}
                        className="p-2 rounded-full bg-green-600 hover:bg-green-700 text-white"
                        disabled={isLoading || !editingCategory.name.trim()}
                      >
                        <Save size={16} />
                      </button>
                      <button 
                        onClick={() => setEditingCategory(null)}
                        className="p-2 rounded-full bg-gray-600 hover:bg-gray-700 text-white"
                        disabled={isLoading}
                      >
                        <XCircle size={16} />
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        onClick={() => setEditingCategory(category)}
                        className="p-2 rounded-full text-blue-400 hover:bg-blue-900/50"
                        disabled={isLoading}
                      >
                        <Edit size={16} />
                      </button>
                      <button 
                        onClick={() => handleDeleteCategory(category.id)}
                        className="p-2 rounded-full text-red-400 hover:bg-red-900/50"
                        disabled={isLoading}
                      >
                        <Trash2 size={16} />
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
