'use client';

import { useState, useEffect } from 'react';
import { CpuChipIcon, CheckCircleIcon, CloudIcon } from '@heroicons/react/24/outline';

interface Model {
  name: string;
  description: string;
  provider: string;
}

interface ModelsResponse {
  models: Model[];
  default_model: string;
  fallback_model: string | null;
  openrouter_configured: boolean;
  openrouter_models: string[];
}

export default function ModelManager() {
  const [data, setData] = useState<ModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeProvider, setActiveProvider] = useState<'ollama' | 'openrouter'>('ollama');

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/models`);
      if (!response.ok) throw new Error('Failed to fetch models');
      const json = await response.json();
      setData(json);
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

  const ollamaModels = data?.models || [];
  const openrouterModels = data?.openrouter_models || [];
  const isOrConfigured = data?.openrouter_configured || false;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Model Management</h2>
        <p className="text-sm text-gray-600">
          {ollamaModels.length} local + {isOrConfigured ? `${openrouterModels.length} cloud` : '0 cloud'} models available
        </p>
      </div>

      {/* Provider Tabs */}
      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveProvider('ollama')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors flex items-center ${
            activeProvider === 'ollama'
              ? 'bg-white text-gray-900 shadow'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <CpuChipIcon className="h-4 w-4 mr-2" />
          Local ({ollamaModels.length})
        </button>
        <button
          onClick={() => setActiveProvider('openrouter')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors flex items-center ${
            activeProvider === 'openrouter'
              ? 'bg-white text-gray-900 shadow'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <CloudIcon className="h-4 w-4 mr-2" />
          Cloud ({isOrConfigured ? openrouterModels.length : 'N/A'})
        </button>
      </div>

      {/* Default Model Banner */}
      <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <CheckCircleIcon className="h-5 w-5 text-primary-600 mr-2" />
            <div>
              <p className="text-sm font-medium text-primary-900">Default Local Model</p>
              <p className="text-lg font-semibold text-primary-700">{data?.default_model}</p>
            </div>
          </div>
          {data?.fallback_model && (
            <div className="text-right">
              <p className="text-sm font-medium text-primary-900">Cloud Fallback</p>
              <p className="text-sm text-primary-700">{data.fallback_model}</p>
            </div>
          )}
        </div>
      </div>

      {/* Models List */}
      {activeProvider === 'ollama' ? (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {ollamaModels.map((model) => (
                <tr key={model.name}>
                  <td className="px-6 py-4">
                    <div className="flex items-center min-w-0">
                      <CpuChipIcon className="h-5 w-5 text-gray-400 mr-3 flex-shrink-0" />
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 break-all">{model.name}</div>
                        <div className="text-xs text-gray-500">{model.description}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {model.name === data?.default_model ? (
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 whitespace-nowrap">Default</span>
                    ) : (
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800 whitespace-nowrap">Available</span>
                    )}
                  </td>
                </tr>
              ))}
              {ollamaModels.length === 0 && (
                <tr><td colSpan={2} className="px-6 py-8 text-center text-gray-500">No Ollama models found. Make sure Ollama is running.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          {!isOrConfigured ? (
            <div className="p-8 text-center">
              <CloudIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-600 font-medium">OpenRouter not configured</p>
              <p className="text-sm text-gray-500 mt-1">
                Add your OpenRouter API key in <strong>Settings &gt; API Keys</strong> to access cloud models.
              </p>
            </div>
          ) : (
            <table className="w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">Provider</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {openrouterModels.map((modelName) => (
                  <tr key={modelName}>
                    <td className="px-6 py-4">
                      <div className="flex items-center min-w-0">
                        <CloudIcon className="h-5 w-5 text-blue-400 mr-3 flex-shrink-0" />
                        <div className="text-sm font-medium text-gray-900 break-all">{modelName}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 whitespace-nowrap">Cloud</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Adding Local Models</h3>
        <p className="text-sm text-blue-700">To add more Ollama models:</p>
        <code className="block mt-2 p-2 bg-blue-100 rounded text-sm text-blue-800">ollama pull model-name</code>
      </div>
    </div>
  );
}
