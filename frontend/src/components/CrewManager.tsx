'use client';

import { useState, useEffect } from 'react';
import { RectangleGroupIcon, PlayIcon, StopIcon } from '@heroicons/react/24/outline';

interface Crew {
  crew_id: string;
  name: string;
  description: string;
  agents: string[];
  status: string;
  tasks_completed: number;
}

export default function CrewManager() {
  const [crews, setCrews] = useState<Crew[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadCrews();
  }, []);

  const loadCrews = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/crews`);
      if (!response.ok) throw new Error('Failed to fetch crews');
      const data = await response.json();
      setCrews(data);
    } catch (err) {
      setError('Failed to load crews');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Crew Management</h2>
        <p className="text-sm text-gray-600">Manage and monitor agent crews</p>
      </div>

      {/* Crews Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {crews.map((crew) => (
          <div
            key={crew.crew_id}
            className="bg-white rounded-lg shadow border border-gray-200 p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center">
                <RectangleGroupIcon className="h-6 w-6 text-primary-500 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">{crew.name}</h3>
              </div>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  crew.status === 'active'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {crew.status}
              </span>
            </div>
            
            <p className="text-sm text-gray-600 mb-3">{crew.description}</p>
            
            <div className="mb-3">
              <p className="text-xs font-medium text-gray-500 mb-1">Agents:</p>
              <div className="flex flex-wrap gap-1">
                {crew.agents.map((agent) => (
                  <span
                    key={agent}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                  >
                    {agent}
                  </span>
                ))}
              </div>
            </div>
            
            <div className="text-xs text-gray-500">
              Tasks completed: {crew.tasks_completed}
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {crews.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <RectangleGroupIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No crews available</p>
        </div>
      )}
    </div>
  );
}
