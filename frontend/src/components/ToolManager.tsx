'use client';

import { useState, useEffect } from 'react';
import { Tool } from '@/types';
import { fetchTools } from '@/utils/api';
import { PlusIcon, PlayIcon, LightBulbIcon, CodeBracketIcon, DocumentTextIcon, XMarkIcon } from '@heroicons/react/24/outline';

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
      const mathMatch = input.match(/(?:calculate|compute|what is|find)\s+(.+?)(?:\?|$)/i) ||
                       input.match(/(\d+\s*[-+*/^]\s*\d+.*?)(?:\?|$)/);
      if (mathMatch) {
        return { expression: mathMatch[1].trim() };
      }
      if (/[\d+\-*/().^]/.test(input)) {
        return { expression: input.replace(/[^\d+\-*/().^\s]/g, '').trim() };
      }
      return null;
      
    case 'search.web':
      const searchMatch = input.match(/(?:search|find|look up)\s+(?:for\s+)?(.+?)(?:\?|$)/i);
      if (searchMatch) {
        return { query: searchMatch[1].trim(), num_results: 5 };
      }
      return { query: input.trim(), num_results: 5 };
      
    case 'file.read':
      const readPathMatch = input.match(/(?:read|show)\s+(?:the\s+)?(?:file\s+)?(?:at\s+)?(?:path\s+)?(.+?)(?:\?|$)/i) ||
                           input.match(/([\/\w\-.]+\.(txt|md|json|py|js|ts|yaml|yml))/i);
      if (readPathMatch) {
        return { path: readPathMatch[1].trim() };
      }
      return null;
      
    case 'file.write':
      const writePathMatch = input.match(/(?:write|save|create)\s+(?:"([^"]+)"|'([^']+)'|to|at)\s+(?:to\s+)?(?:file\s+)?(.+?)(?:\?|$)/i);
      if (writePathMatch) {
        const content = writePathMatch[1] || writePathMatch[2] || '';
        const path = writePathMatch[3] || input.match(/([\/\w\-.]+)/)?.[1] || '/tmp/output.txt';
        return { path: path.trim(), content: content.trim() };
      }
      const simpleMatch = input.match(/["']([^"']+)["']\s+(?:to|in)\s+([\/\w\-.]+)/i);
      if (simpleMatch) {
        return { path: simpleMatch[2].trim(), content: simpleMatch[1].trim() };
      }
      return null;
      
    default:
      return null;
  }
}

interface ToolInstructions {
  can_add_dynamically: boolean;
  instructions: string;
  file_structure: Record<string, string>;
  example_code: string;
}

export default function ToolManager() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [instructions, setInstructions] = useState<ToolInstructions | null>(null);

  useEffect(() => {
    loadTools();
    loadInstructions();
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

  const loadInstructions = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/tools/instructions`);
      if (response.ok) {
        const data = await response.json();
        setInstructions(data);
      }
    } catch (err) {
      console.error('Failed to load instructions');
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

      {/* Add Tool Modal with Instructions */}
      {showAddModal && instructions && (
        <AddToolModal
          instructions={instructions}
          onClose={() => setShowAddModal(false)}
          onToolAdded={loadTools}
        />
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

// Add Tool Modal with Instructions
function AddToolModal({ 
  instructions, 
  onClose,
  onToolAdded 
}: { 
  instructions: ToolInstructions;
  onClose: () => void;
  onToolAdded: () => void;
}) {
  const [activeTab, setActiveTab] = useState<'instructions' | 'dynamic' | 'manual'>('instructions');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-medium text-gray-900">Add New Tool</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('instructions')}
              className={`py-4 px-6 text-sm font-medium border-b-2 ${
                activeTab === 'instructions'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <DocumentTextIcon className="h-4 w-4 inline mr-2" />
              Instructions
            </button>
            <button
              onClick={() => setActiveTab('dynamic')}
              className={`py-4 px-6 text-sm font-medium border-b-2 ${
                activeTab === 'dynamic'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <CodeBracketIcon className="h-4 w-4 inline mr-2" />
              Add Dynamically
            </button>
            <button
              onClick={() => setActiveTab('manual')}
              className={`py-4 px-6 text-sm font-medium border-b-2 ${
                activeTab === 'manual'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Manual Setup
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'instructions' && (
            <div className="prose prose-sm max-w-none">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <h4 className="text-blue-900 font-medium mb-2">Two Ways to Add Tools</h4>
                <ol className="list-decimal list-inside text-blue-800 space-y-1">
                  <li><strong>Dynamic Addition</strong> - Add via API (no restart needed)</li>
                  <li><strong>Manual Setup</strong> - Create Python files (requires restart)</li>
                </ol>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900">File Structure</h4>
                  <ul className="mt-2 space-y-1 text-sm text-gray-600 bg-gray-50 p-3 rounded">
                    {Object.entries(instructions.file_structure).map(([key, value]) => (
                      <li key={key}><strong>{key}:</strong> {value}</li>
                    ))}
                  </ul>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h4 className="font-medium text-yellow-900 mb-2">Important Notes</h4>
                  <ul className="list-disc list-inside text-sm text-yellow-800 space-y-1">
                    <li>Tools added manually require a server restart</li>
                    <li>Tools added dynamically are available immediately</li>
                    <li>All tools must extend the BaseTool class</li>
                    <li>Implement execute() and get_schema() methods</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'dynamic' && (
            <DynamicToolForm 
              onSuccess={() => {
                onToolAdded();
                onClose();
              }}
              onError={setCreateError}
            />
          )}

          {activeTab === 'manual' && (
            <div className="space-y-6">
              <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
                <pre className="text-sm whitespace-pre-wrap">{instructions.example_code}</pre>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium text-gray-900">Steps to Add Tool Manually:</h4>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li>Create a new file in <code className="bg-gray-100 px-1 rounded">backend/src/skills/library/</code></li>
                  <li>Copy the example code above and customize it</li>
                  <li>Register your tool in <code className="bg-gray-100 px-1 rounded">backend/src/api/app.py</code></li>
                  <li>Restart the server with <code className="bg-gray-100 px-1 rounded">./start.sh</code></li>
                </ol>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h4 className="font-medium text-red-900 mb-2">Restart Required</h4>
                <p className="text-sm text-red-800">
                  After adding a tool manually, you must restart the server for changes to take effect.
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// Dynamic Tool Form
function DynamicToolForm({ onSuccess, onError }: { onSuccess: () => void; onError: (msg: string) => void }) {
  const [toolId, setToolId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [dangerLevel, setDangerLevel] = useState('safe');
  const [parameters, setParameters] = useState('[\n  {\n    "name": "param1",\n    "type": "string",\n    "description": "Parameter description",\n    "required": true\n  }\n]');
  const [code, setCode] = useState(`# Implement your tool logic here
# Available imports: ToolResult, logger

# Example:
result = f"Processed {param1}"
return ToolResult(
    success=True,
    result=result,
    metadata={"input": param1}
)`);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    onError('');

    try {
      let parsedParams;
      try {
        parsedParams = JSON.parse(parameters);
      } catch {
        onError('Invalid JSON in parameters field');
        setIsSubmitting(false);
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/tools`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_id: toolId,
          name,
          description,
          danger_level: dangerLevel,
          parameters: parsedParams,
          code
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create tool');
      }

      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to create tool');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Tool ID</label>
          <input
            type="text"
            value={toolId}
            onChange={(e) => setToolId(e.target.value)}
            required
            placeholder="custom.my_tool"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">Format: category.tool_name</p>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="My Tool"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          rows={2}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Danger Level</label>
        <select
          value={dangerLevel}
          onChange={(e) => setDangerLevel(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
        >
          <option value="safe">Safe (Read-only)</option>
          <option value="normal">Normal (Standard operations)</option>
          <option value="destructive">Destructive (Can modify/delete)</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Parameters (JSON)</label>
        <textarea
          value={parameters}
          onChange={(e) => setParameters(e.target.value)}
          required
          rows={6}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm font-mono"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Tool Code (Python)</label>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          required
          rows={10}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm font-mono"
        />
        <p className="text-xs text-gray-500 mt-1">
          Write the body of the execute() method. Use 'return ToolResult(success=True, result=...)' 
        </p>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-xs text-yellow-800">
          <strong>Security Warning:</strong> This executes arbitrary Python code. 
          Only add tools from trusted sources in production.
        </p>
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Creating...' : 'Create Tool'}
        </button>
      </div>
    </form>
  );
}

// Test Modal Component
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
        if (!parsedParams) {
          setError('Could not parse your input. Please try rephrasing or switch to JSON mode.');
          setLoading(false);
          return;
        }
        params = parsedParams;
      } else {
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Parameters (JSON)
              </label>
              <textarea
                value={parameters}
                onChange={(e) => setParameters(e.target.value)}
                rows={6}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 font-mono text-sm"
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
  );
}