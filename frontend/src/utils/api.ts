const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchAgents(): Promise<Agent[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/`);
  if (!response.ok) throw new Error('Failed to fetch agents');
  return response.json();
}

export async function fetchTools(): Promise<Tool[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/tools/`);
  if (!response.ok) throw new Error('Failed to fetch tools');
  return response.json();
}

export async function executeTask(query: string): Promise<TaskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) throw new Error('Failed to execute task');
  return response.json();
}

export async function runAgent(agentId: string, input: string): Promise<{ output: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/${agentId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input_text: input }),
  });
  if (!response.ok) throw new Error('Failed to run agent');
  return response.json();
}

export async function executeTool(toolId: string, parameters: Record<string, unknown>): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/tools/${toolId}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parameters }),
  });
  if (!response.ok) throw new Error('Failed to execute tool');
  return response.json();
}

import { Agent, Tool, TaskResponse } from '@/types';