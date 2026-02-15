'use client';

import { useState, useEffect } from 'react';
import { Agent } from '@/types';
import { fetchAgents } from '@/utils/api';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';

interface AgentConfig {
  agent_id: string;
  name: string;
  description: string;
  model: string;
  temperature: number;
  allowed_tools: string[];
}

export default function AgentManager() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null);

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const data = await fetchAgents();
      setAgents(data);
    } catch (err) {
      setError('Failed to load agents');
    } finally {
      setLoading(false);
    }
  };

  const handleAddAgent = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    const newAgent: AgentConfig = {
      agent_id: formData.get('agent_id') as string,
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      model: formData.get('model') as string,
      temperature: parseFloat(formData.get('temperature') as string),
      allowed_tools: (formData.get('allowed_tools') as string).split(',').map(t => t.trim()).filter(Boolean),
    };

    // TODO: Call API to create agent
    console.log('Creating agent:', newAgent);
    setShowAddModal(false);
    // Refresh agents list
    await loadAgents();
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
          <h2 className="text-2xl font-bold text-gray-900">Agent Management</h2>
          <p className="text-sm text-gray-600">Configure and manage your AI agents</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Add Agent
        </button>
      </div>

      {/* Agents List */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Agent
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Model
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tools
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {agents.map((agent) => (
              <tr key={agent.agent_id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                      <span className="text-primary-600 font-medium">
                        {agent.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">{agent.name}</div>
                      <div className="text-sm text-gray-500">{agent.description}</div>
                      <div className="text-xs text-gray-400">ID: {agent.agent_id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {agent.model}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex flex-wrap gap-1">
                    {agent.allowed_tools.length > 0 ? (
                      agent.allowed_tools.map((tool) => (
                        <span
                          key={tool}
                          className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700"
                        >
                          {tool}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-gray-400">No tools</span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => setEditingAgent(agent as AgentConfig)}
                    className="text-primary-600 hover:text-primary-900 mr-3"
                  >
                    <PencilIcon className="h-5 w-5" />
                  </button>
                  <button className="text-red-600 hover:text-red-900">
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add/Edit Agent Modal */}
      {(showAddModal || editingAgent) && (
        <AgentModal
          agent={editingAgent}
          onClose={() => {
            setShowAddModal(false);
            setEditingAgent(null);
          }}
          onSave={async (agentData) => {
            console.log('Saving agent:', agentData);
            // TODO: Call API to create/update agent
            setShowAddModal(false);
            setEditingAgent(null);
            await loadAgents();
          }}
        />
      )}
    </div>
  )
}

// Agent Modal Component for Add/Edit
function AgentModal({ 
  agent, 
  onClose, 
  onSave 
}: { 
  agent: AgentConfig | null;
  onClose: () => void;
  onSave: (agent: AgentConfig) => void;
}) {
  const isEditing = !!agent;
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    const agentData: AgentConfig = {
      agent_id: (formData.get('agent_id') as string) || agent?.agent_id || '',
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      model: formData.get('model') as string,
      temperature: parseFloat(formData.get('temperature') as string),
      allowed_tools: (formData.get('allowed_tools') as string).split(',').map(t => t.trim()).filter(Boolean),
    };
    
    onSave(agentData);
  };

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">
            {isEditing ? 'Edit Agent' : 'Add New Agent'}
          </h3>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Agent ID</label>
              <input
                type="text"
                name="agent_id"
                required
                defaultValue={agent?.agent_id || ''}
                readOnly={isEditing}
                placeholder="my-custom-agent"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 disabled:bg-gray-100"
              />
              {isEditing && (
                <p className="mt-1 text-xs text-gray-500">Agent ID cannot be changed</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                type="text"
                name="name"
                required
                defaultValue={agent?.name || ''}
                placeholder="My Custom Agent"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              name="description"
              rows={2}
              defaultValue={agent?.description || ''}
              placeholder="What does this agent do?"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Model</label>
              <select
                name="model"
                defaultValue={agent?.model || 'llama3.1:8b'}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              >
                <option value="llama3.1:8b">llama3.1:8b</option>
                <option value="qwen2.5-coder:14b">qwen2.5-coder:14b</option>
                <option value="phi3.5:3.8b">phi3.5:3.8b</option>
                <option value="deepseek-coder-v2:16b">deepseek-coder-v2:16b</option>
                <option value="gemma3:12b">gemma3:12b</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Temperature (0.0 - 2.0)
              </label>
              <input
                type="number"
                name="temperature"
                min="0"
                max="2"
                step="0.1"
                defaultValue={agent?.temperature || 0.7}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Allowed Tools (comma-separated)
            </label>
            <input
              type="text"
              name="allowed_tools"
              defaultValue={agent?.allowed_tools?.join(', ') || ''}
              placeholder="calculator.compute, file.read, search.web"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Available tools: calculator.compute, search.web, file.read, file.write
            </p>
          </div>
          
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700"
            >
              {isEditing ? 'Save Changes' : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}