'use client';

import { useState, useEffect } from 'react';
import { Agent } from '@/types';
import { fetchAgents, runAgent } from '@/utils/api';

export default function AgentPanel() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [agentInput, setAgentInput] = useState('');
  const [agentOutput, setAgentOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const data = await fetchAgents();
      setAgents(data);
      if (data.length > 0) {
        setSelectedAgent(data[0].agent_id);
      }
    } catch (err) {
      setError('Failed to load agents');
    }
  };

  const handleRunAgent = async () => {
    if (!selectedAgent || !agentInput.trim()) return;

    setIsLoading(true);
    setError('');
    setAgentOutput('');

    try {
      const result = await runAgent(selectedAgent, agentInput);
      setAgentOutput(result.output);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run agent');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border">
      <div className="p-4 border-b bg-gray-50 rounded-t-lg">
        <h2 className="text-lg font-semibold text-gray-800">Agent Panel</h2>
        <p className="text-sm text-gray-600">Run agents directly</p>
      </div>

      <div className="p-4 space-y-4">
        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Select Agent
          </label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {agents.map((agent) => (
              <option key={agent.agent_id} value={agent.agent_id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>

        {selectedAgent && (
          <div className="text-sm text-gray-600">
            {agents.find((a) => a.agent_id === selectedAgent)?.description}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Input
          </label>
          <textarea
            value={agentInput}
            onChange={(e) => setAgentInput(e.target.value)}
            placeholder="Enter input for the agent..."
            rows={3}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
          />
        </div>

        <button
          onClick={handleRunAgent}
          disabled={isLoading || !selectedAgent || !agentInput.trim()}
          className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Running...' : 'Run Agent'}
        </button>

        {agentOutput && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Output
            </label>
            <div className="bg-gray-50 p-3 rounded-lg text-sm whitespace-pre-wrap max-h-48 overflow-y-auto">
              {agentOutput}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}