'use client';

import { useState, useEffect } from 'react';
import { Tool } from '@/types';
import { fetchTools, executeTool } from '@/utils/api';

export default function ToolTester() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedTool, setSelectedTool] = useState<string>('');
  const [parameters, setParameters] = useState('');
  const [result, setResult] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const data = await fetchTools();
      setTools(data);
      if (data.length > 0) {
        setSelectedTool(data[0].tool_id);
      }
    } catch (err) {
      setError('Failed to load tools');
    }
  };

  const handleExecuteTool = async () => {
    if (!selectedTool) return;

    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      let params = {};
      if (parameters.trim()) {
        try {
          params = JSON.parse(parameters);
        } catch {
          setError('Invalid JSON in parameters');
          setIsLoading(false);
          return;
        }
      }

      const data = await executeTool(selectedTool, params);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute tool');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border">
      <div className="p-4 border-b bg-gray-50 rounded-t-lg">
        <h2 className="text-lg font-semibold text-gray-800">Tool Tester</h2>
        <p className="text-sm text-gray-600">Test tools directly</p>
      </div>

      <div className="p-4 space-y-4">
        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Select Tool
          </label>
          <select
            value={selectedTool}
            onChange={(e) => setSelectedTool(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {tools.map((tool) => (
              <option key={tool.tool_id} value={tool.tool_id}>
                {tool.name}
              </option>
            ))}
          </select>
        </div>

        {selectedTool && (
          <div className="text-sm text-gray-600">
            <p>{tools.find((t) => t.tool_id === selectedTool)?.description}</p>
            <span
              className={`inline-block mt-1 px-2 py-1 rounded text-xs ${
                tools.find((t) => t.tool_id === selectedTool)?.danger_level ===
                'destructive'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {tools.find((t) => t.tool_id === selectedTool)?.danger_level}
            </span>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Parameters (JSON)
          </label>
          <textarea
            value={parameters}
            onChange={(e) => setParameters(e.target.value)}
            placeholder='{"key": "value"}'
            rows={3}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none font-mono text-sm"
          />
        </div>

        <button
          onClick={handleExecuteTool}
          disabled={isLoading || !selectedTool}
          className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Executing...' : 'Execute Tool'}
        </button>

        {result && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Result
            </label>
            <pre className="bg-gray-50 p-3 rounded-lg text-xs overflow-x-auto max-h-48">
              {String(JSON.stringify(result, null, 2))}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}