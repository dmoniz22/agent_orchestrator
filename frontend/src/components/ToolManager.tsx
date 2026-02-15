'use client';

import { useState, useEffect } from 'react';
import { Tool } from '@/types';
import { fetchTools } from '@/utils/api';

export default function ToolManager() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const data = await fetchTools();
      setTools(data);
    } catch (err) {
      setError('Failed to load tools');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md border p-4">
        <p className="text-sm text-gray-600">Loading tools...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md border p-4">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md border p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Available Tools</h3>
      
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {tools.length === 0 ? (
          <p className="text-sm text-gray-500">No tools available</p>
        ) : (
          tools.map((tool) => (
            <div
              key={tool.tool_id}
              className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-700 truncate">{tool.name}</p>
                <p className="text-xs text-gray-500 truncate">{tool.tool_id}</p>
              </div>
              <span
                className={`ml-2 px-2 py-0.5 text-xs rounded ${
                  tool.danger_level === 'destructive'
                    ? 'bg-red-100 text-red-700'
                    : tool.danger_level === 'normal'
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-green-100 text-green-700'
                }`}
              >
                {tool.danger_level}
              </span>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 pt-3 border-t text-xs text-gray-500">
        <p>Total tools: {tools.length}</p>
      </div>
    </div>
  );
}