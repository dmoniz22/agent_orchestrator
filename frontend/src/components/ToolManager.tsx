'use client';

import { useState, useEffect } from 'react';
import { Tool } from '@/types';
import { fetchTools } from '@/utils/api';
import { PlusIcon, PlayIcon, TrashIcon, LightBulbIcon } from '@heroicons/react/24/outline';

// Tool examples for natural language parsing
const toolExamples: Record<string, string[]> = {
  'calculator.compute': [
    'Calculate 2 + 2',
    'What is the square root of 16?',
    'Compute 15 * 23 + 7',
    'sin of 90 degrees'
  ],
  'search.web': [
    'Search for latest AI news',
    'Find information about Python asyncio',
    'Search: weather forecast',
    'Look up React documentation'
  ],
  'file.read': [
    'Read the file /tmp/test.txt',
    'Show me the contents of README.md',
    'Read file at path /home/user/document.txt'
  ],
  'file.write': [
    'Write "Hello World" to /tmp/hello.txt',
    'Create a file at /tmp/output.txt with content "test data"',
    'Save "configuration data" to config.json'
  ]
};

// Parse natural language to tool parameters
function parseNaturalLanguage(toolId: string, input: string): Record<string, any> | null {
  const lowerInput = input.toLowerCase();
  
  switch (toolId) {
    case 'calculator.compute':
      // Extract mathematical expression
      const mathMatch = input.match(/(?:calculate|compute|what is|find)\s+(.+?)(?:\?|$)/i) ||
                       input.match(/(\d+\s*[-+*/^]\s*\d+.*?)(?:\?|$)/);
      if (mathMatch) {
        return { expression: mathMatch[1].trim() };
      }
      // If it looks like a math expression
      if (/[\d+\-*/().^]/.test(input)) {
        return { expression: input.replace(/[^\d+\-*/().^\s]/g, '').trim() };
      }
      return null;
      
    case 'search.web':
      // Extract search query
      const searchMatch = input.match(/(?:search|find|look up)\s+(?:for\s+)?(.+?)(?:\?|$)/i);
      if (searchMatch) {
        return { query: searchMatch[1].trim(), num_results: 5 };
      }
      return { query: input.trim(), num_results: 5 };
      
    case 'file.read':
      // Extract file path
      const readPathMatch = input.match(/(?:read|show)\s+(?:the\s+)?(?:file\s+)?(?:at\s+)?(?:path\s+)?(.+?)(?:\?|$)/i) ||
                           input.match(/([\/\w\-.]+\.(txt|md|json|py|js|ts|yaml|yml))/i);
      if (readPathMatch) {
        return { path: readPathMatch[1].trim() };
      }
      return null;
      
    case 'file.write':
      // Extract file path and content
      const writePathMatch = input.match(/(?:write|save|create)\s+(?:"([^"]+)"|'([^']+)'|to|at)\s+(?:to\s+)?(?:file\s+)?(.+?)(?:\?|$)/i);
      if (writePathMatch) {
        const content = writePathMatch[1] || writePathMatch[2] || '';
        const path = writePathMatch[3] || input.match(/([\/\w\-.]+)/)?.[1] || '/tmp/output.txt';
        return { path: path.trim(), content: content.trim() };
      }
      // Try simpler pattern: "text" to path
      const simpleMatch = input.match(/["']([^"']+)["']\s+(?:to|in)\s+([\/\w\-.]+)/i);
      if (simpleMatch) {
        return { path: simpleMatch[2].trim(), content: simpleMatch[1].trim() };
      }
      return null;
      
    default:
      return null;
  }
}

export default function ToolManager() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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
        <div className="text-sm text-gray-500">
          {tools.length} tool{tools.length !== 1 ? 's' : ''} available
        </div>
      </div>

      {/* Tools Grid - responsive columns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {tools.map((tool) => (
          <div
            key={tool.tool_id}
            className="bg-white rounded-lg shadow border border-gray-200 p-4 hover:shadow-md transition-shadow min-w-0"
          >
            <div className="flex justify-between items-start mb-2 gap-2">
              <h3 className="text-lg font-medium text-gray-900 truncate">{tool.name}</h3>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full flex-shrink-0 ${
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
            
            <p className="text-sm text-gray-600 mb-3 line-clamp-2">{tool.description}</p>
            
            <div className="text-xs text-gray-500 mb-4 truncate">
              ID: <code className="bg-gray-100 px-1 rounded break-all">{tool.tool_id}</code>
            </div>
            
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => handleTestTool(tool)}
                className="flex items-center px-3 py-1.5 text-sm text-primary-600 hover:text-primary-800 hover:bg-primary-50 rounded"
              >
                <PlayIcon className="h-4 w-4 mr-1" />
                Test
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {tools.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No tools available</p>
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

// Test Modal Component with Natural Language Support
function ToolTestModal({ tool, onClose }: { tool: Tool; onClose: () => void }) {
  const [inputMode, setInputMode] = useState<'natural' | 'json'>('natural');
  const [naturalInput, setNaturalInput] = useState('');
  const [parameters, setParameters] = useState('{}');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [parsedParams, setParsedParams] = useState<Record<string, any> | null>(null);

  const examples = toolExamples[tool.tool_id] || ['Enter your request...'];

  const handleNaturalInputChange = (value: string) => {
    setNaturalInput(value);
    const parsed = parseNaturalLanguage(tool.tool_id, value);
    setParsedParams(parsed);
    if (parsed) {
      setParameters(JSON.stringify(parsed, null, 2));
    }
  };

  const handleTest = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      let params = {};
      
      if (inputMode === 'natural') {
        // Use parsed parameters from natural language
        if (!parsedParams) {
          setError('Could not parse your input. Please try rephrasing or switch to JSON mode.');
          setLoading(false);
          return;
        }
        params = parsedParams;
      } else {
        // Parse JSON input
        try {
          params = JSON.parse(parameters);
        } catch {
          setError('Invalid JSON in parameters');
          setLoading(false);
          return;
        }
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
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Test Tool: {tool.name}</h3>
          <p className="text-sm text-gray-600">{tool.description}</p>
        </div>
        
        <div className="p-6 space-y-4">
          {/* Input Mode Toggle */}
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
            <button
              onClick={() => setInputMode('natural')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                inputMode === 'natural'
                  ? 'bg-white text-gray-900 shadow'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Natural Language
            </button>
            <button
              onClick={() => setInputMode('json')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                inputMode === 'json'
                  ? 'bg-white text-gray-900 shadow'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              JSON
            </button>
          </div>

          {inputMode === 'natural' ? (
            <>
              {/* Natural Language Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Describe what you want to do
                </label>
                <textarea
                  value={naturalInput}
                  onChange={(e) => handleNaturalInputChange(e.target.value)}
                  rows={3}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  placeholder={examples[0]}
                />
                
                {/* Examples */}
                <div className="mt-3">
                  <p className="text-xs font-medium text-gray-500 mb-2 flex items-center">
                    <LightBulbIcon className="h-4 w-4 mr-1" />
                    Try these examples:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {examples.slice(1).map((example, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleNaturalInputChange(example)}
                        className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Parsed Parameters Preview */}
                {parsedParams && (
                  <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                    <p className="text-xs font-medium text-green-800 mb-1">Parsed Parameters:</p>
                    <pre className="text-xs text-green-700 overflow-x-auto">
                      {JSON.stringify(parsedParams, null, 2)}
                    </pre>
                  </div>
                )}

                {!parsedParams && naturalInput && (
                  <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                    <p className="text-xs text-yellow-800">
                      Could not parse input. Try rephrasing or switch to JSON mode.
                    </p>
                  </div>
                )}
              </div>
            </>
          ) : (
            /* JSON Input */
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Parameters (JSON)
              </label>
              <textarea
                value={parameters}
                onChange={(e) => setParameters(e.target.value)}
                rows={6}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 font-mono text-sm"
                placeholder={'{\n  "param1": "value1",\n  "param2": "value2"\n}'}
              />
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {result && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Result</label>
              <pre className="bg-gray-50 p-3 rounded-md text-xs overflow-x-auto border border-gray-200">
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
            disabled={loading || (inputMode === 'natural' && !parsedParams)}
            className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Testing...' : 'Test Tool'}
          </button>
        </div>
      </div>
    </div>
  )
}