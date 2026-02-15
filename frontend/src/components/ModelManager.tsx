'use client';

import { useState, useEffect } from 'react';
import { CpuChipIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

interface Model {
  name: string;
  description: string;
}

export default function ModelManager() {
  const [models, setModels] = useState<Model[]>([]);
  const [defaultModel, setDefaultModel] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/models`);
      if (!response.ok) throw new Error('Failed to fetch models');
      const data = await response.json();
      setModels(data.models);
      setDefaultModel(data.default_model);
    } catch (err) {
      setError('Failed to load models');
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
        <h2 className="text-2xl font-bold text-gray-900">Model Management</h2>
        <p className="text-sm text-gray-600">
          Available Ollama models ({models.length} total)
        </p>
      </div>

      {/* Default Model Banner */}
      <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
        <div className="flex items-center">
          <CheckCircleIcon className="h-5 w-5 text-primary-600 mr-2" />
          <div>
            <p className="text-sm font-medium text-primary-900">Default Model</p>
            <p className="text-lg font-semibold text-primary-700">{defaultModel}</p>
          </div>
        </div>
      </div>

      {/* Models List */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Model
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {models.map((model) => (
              <tr key={model.name}>
                <td className="px-6 py-4">
                  <div className="flex items-center min-w-0">
                    <CpuChipIcon className="h-5 w-5 text-gray-400 mr-3 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-900 break-all">{model.name}</div>
                      <div className="text-xs text-gray-500 break-words">{model.description}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  {model.name === defaultModel ? (
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 whitespace-nowrap">
                      Default
                    </span>
                  ) : (
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800 whitespace-nowrap">
                      Available
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Adding Models</h3>
        <p className="text-sm text-blue-700">
          To add more models, use the Ollama CLI:
        </p>
        <code className="block mt-2 p-2 bg-blue-100 rounded text-sm text-blue-800">
          ollama pull model-name
        </code>
        <p className="mt-2 text-sm text-blue-600">
          Then refresh this page to see the new model.
        </p>
      </div>
    </div>
  )
}