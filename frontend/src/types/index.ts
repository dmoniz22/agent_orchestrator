export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  model: string;
  allowed_tools: string[];
}

export interface Tool {
  tool_id: string;
  name: string;
  description: string;
  danger_level: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  response: string;
  agents_invoked?: string[];
  tools_used?: string[];
  error?: string;
}