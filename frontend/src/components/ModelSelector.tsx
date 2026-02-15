'use client';

import { useState, useEffect } from 'react';

interface Model {
  name: string;
  description: string;
}

export default function ModelSelector() {
  const [models, setModels] = useState<Model[]>([]);
  const [defaultModel, setDefaultModel] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
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
      setSelectedModel(data.default_model);
    } catch (err) {
      setError('Failed to load models');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md border p-4">
        <p className="text-sm text-gray-600">Loading models...</p>
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
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Model Selection</h3>
      
      <div className="space-y-2">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Active Model</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {models.map((model) => (
              <option key={model.name} value={model.name}>
                {model.name} {model.name === defaultModel ? '(default)' : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-gray-500">
          <p>Available models: {models.length}</p>
          {models.length === 0 && (
            <p className="text-red-500 mt-1">
              No models found. Make sure Ollama is running.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}