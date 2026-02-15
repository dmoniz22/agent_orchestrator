'use client';

import { useState, useEffect } from 'react';
import { Tool } from '@/types';
import { fetchTools } from '@/utils/api';
import { PlusIcon, PlayIcon, TrashIcon } from '@heroicons/react/24/outline';

export default function ToolManager() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);

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

  const handleTestTool = (tool: Tool) => {
    setSelectedTool(tool);
    setShowTestModal(true);
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
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Tool Management</h2>
          <p className="text-sm text-gray-600">Manage and test available tools</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Add Tool
        </button>
      </div>

      {/* Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tools.map((tool) => (
          <div
            key={tool.tool_id}
            className="bg-white rounded-lg shadow border border-gray-200 p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-lg font-medium text-gray-900">{tool.name}</h3>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  tool.danger_level === 'destructive'
                    ? 'bg-red-100 text-red-800'
                    : tool.danger_level === 'normal'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
                }`}
              >
                {tool.danger_level}
              </span>
            </div>
            
            <p className="text-sm text-gray-600 mb-3">{tool.description}</p>
            
            <div className="text-xs text-gray-500 mb-4">
              ID: <code className="bg-gray-100 px-1 rounded">{tool.tool_id}</code>
            </div>
            
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => handleTestTool(tool)}
                className="flex items-center px-3 py-1.5 text-sm text-primary-600 hover:text-primary-800 hover:bg-primary-50 rounded"
              >
                <PlayIcon className="h-4 w-4 mr-1" />
                Test
              </button>
              <button className="flex items-center px-3 py-1.5 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded">
                <TrashIcon className="h-4 w-4 mr-1" />
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {tools.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <WrenchIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No tools</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by adding a new tool.</p>
        </div>
      )}

      {/* Add Tool Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Add New Tool</h3>
            </div>
            
            <div className="p-6">
              <p className="text-sm text-gray-600 mb-4">
                Tool creation requires backend implementation. This feature allows you to register custom tools that can be used by agents.
              </p>
              
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                <p className="text-sm text-yellow-800">
                  <strong>Note:</strong> To add custom tools, you need to implement the tool class in the backend and register it through the API.
                </p>
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Tool Modal */}
      {showTestModal && selectedTool && (
        <ToolTestModal
          tool={selectedTool}
          onClose={() => setShowTestModal(false)}
        />
      )}
    </div>
  )
}

// Test Modal Component
function ToolTestModal({ tool, onClose }: { tool: Tool; onClose: () => void }) {
  const [parameters, setParameters] = useState('{}');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTest = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      let params = {};
      try {
        params = JSON.parse(parameters);
      } catch {
        setError('Invalid JSON in parameters');
        setLoading(false);
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/tools/${tool.tool_id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parameters: params }),
      });

      if (!response.ok) throw new Error('Failed to execute tool');
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute tool');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Test Tool: {tool.name}</h3>
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Parameters (JSON)
            </label>
            <textarea
              value={parameters}
              onChange={(e) => setParameters(e.target.value)}
              rows={6}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 font-mono text-sm"
              placeholder={'{\n  "param1": "value1",\n  "param2": "value2"\n}'}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {result && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Result</label>
              <pre className="mt-1 bg-gray-50 p-3 rounded-md text-xs overflow-x-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
        
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
          <button
            onClick={handleTest}
            disabled={loading}
            className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Testing...' : 'Test Tool'}
          </button>
        </div>
      </div>
    </div>
  )
}

import { WrenchIcon } from '@heroicons/react/24/outline'