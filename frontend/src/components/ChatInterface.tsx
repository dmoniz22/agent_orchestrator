'use client';

import { useState, useRef, useEffect } from 'react';
import { Message, TaskResponse } from '@/types';
import { executeTask } from '@/utils/api';

const SESSION_STORAGE_KEY = 'omni_chat_session';
const MESSAGES_STORAGE_KEY = 'omni_chat_messages';

function generateSessionId(): string {
  return 'session_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
}

function getStoredSessionId(): string {
  if (typeof window === 'undefined') return generateSessionId();
  
  let sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  return sessionId;
}

function loadStoredMessages(): Message[] {
  if (typeof window === 'undefined') return [];
  
  const stored = localStorage.getItem(MESSAGES_STORAGE_KEY);
  if (!stored) return [];
  
  try {
    const messages = JSON.parse(stored);
    return messages.map((m: any) => ({
      ...m,
      timestamp: new Date(m.timestamp)
    }));
  } catch {
    return [];
  }
}

function saveMessages(messages: Message[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(MESSAGES_STORAGE_KEY, JSON.stringify(messages));
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [isLoaded, setIsLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadData() {
      const storedSessionId = getStoredSessionId();
      setSessionId(storedSessionId);
      
      // Load local messages first
      const localMessages = loadStoredMessages();
      setMessages(localMessages);
      
      // Then fetch from backend to get full history
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/sessions/${storedSessionId}/history`);
        if (res.ok) {
          const data = await res.json();
          if (data.messages && data.messages.length > 0) {
            // Merge with local messages, removing duplicates
            const backendMessages = data.messages.map((m: any) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              timestamp: m.timestamp ? new Date(m.timestamp) : new Date()
            }));
            
            // Check if we need to merge
            const localIds = new Set(localMessages.map(m => m.id));
            const newFromBackend = backendMessages.filter((m: any) => !localIds.has(m.id));
            if (newFromBackend.length > 0) {
              setMessages([...localMessages, ...newFromBackend]);
            }
          }
        }
      } catch (e) {
        // Silently fail - local messages will still show
      }
      
      setIsLoaded(true);
    }
    loadData();
  }, []);

  useEffect(() => {
    if (isLoaded) {
      saveMessages(messages);
    }
  }, [messages, isLoaded]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await executeTask(input, sessionId);
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response || response.error || 'No response',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border h-[calc(100vh-12rem)] flex flex-col">
      {/* Chat Header */}
      <div className="p-4 border-b bg-gray-50 rounded-t-lg flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Chat</h2>
          <p className="text-sm text-gray-600">Ask anything to the multi-agent system</p>
        </div>
        <button
          onClick={() => {
            setMessages([]);
            localStorage.removeItem(MESSAGES_STORAGE_KEY);
          }}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Clear Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg mb-2">Welcome to OMNI!</p>
            <p className="text-sm">Start a conversation by typing below.</p>
            <div className="mt-4 space-y-2 text-sm">
              <p className="text-gray-400">Try asking:</p>
              <button
                onClick={() => setInput('What is the weather today?')}
                className="block mx-auto text-primary-600 hover:underline"
              >
                "What is the weather today?"
              </button>
              <button
                onClick={() => setInput('Write a Python function to calculate fibonacci')}
                className="block mx-auto text-primary-600 hover:underline"
              >
                "Write a Python function..."
              </button>
              <button
                onClick={() => setInput('Research the latest AI developments')}
                className="block mx-auto text-primary-600 hover:underline"
              >
                "Research AI developments..."
              </button>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              <span className="text-xs opacity-70 mt-1 block">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2 flex items-center space-x-2">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}