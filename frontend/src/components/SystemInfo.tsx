'use client';

import { useState, useEffect } from 'react';
import { ServerStackIcon, ClockIcon, CpuChipIcon, GlobeAltIcon, UserGroupIcon } from '@heroicons/react/24/outline';

interface SystemInfo {
  python_version: string;
  platform: string;
  architecture: string;
  processor: string;
  start_time: string;
}

interface SystemStatus {
  version: string;
  environment: string;
  status: string;
  timestamp: string;
}

interface ActiveTask {
  task_id: string;
  status: string;
  input: string | null;
  started_at: string | null;
}

export default function SystemInfo() {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [activeTasks, setActiveTasks] = useState<ActiveTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSystemInfo();
    const interval = setInterval(loadActiveAgents, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadSystemInfo = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const [infoRes, statusRes, agentsRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/system/info`),
        fetch(`${apiUrl}/api/v1/system/status`),
        fetch(`${apiUrl}/api/v1/agents/active`),
      ]);
      
      if (!infoRes.ok || !statusRes.ok) {
        throw new Error('Failed to fetch system info');
      }
      
      const [infoData, statusData, agentsData] = await Promise.all([
        infoRes.json(),
        statusRes.json(),
        agentsRes.json().catch(() => ({ active_tasks: [] })),
      ]);

      setInfo(infoData);
      setStatus(statusData);
      setActiveTasks(agentsData.active_tasks || []);
    } catch (err) {
      setError('Failed to load system information');
    } finally {
      setLoading(false);
    }
  };

  const loadActiveAgents = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/v1/agents/active`);
      const data = await res.json();
      setActiveTasks(data.active_tasks || []);
    } catch (err) {
      // Silently fail for polling
    }
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
      <div>
        <h2 className="text-2xl font-bold text-gray-900">System Information</h2>
        <p className="text-sm text-gray-600">System status and configuration</p>
      </div>

      {/* Status Card */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <ServerStackIcon className="h-6 w-6 text-primary-500 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">OMNI System</h3>
          </div>
          <span
            className={`px-3 py-1 text-sm font-medium rounded-full ${
              status?.status === 'operational'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {status?.status || 'Unknown'}
          </span>
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Version</p>
            <p className="font-medium">{status?.version || 'N/A'}</p>
          </div>
          <div>
            <p className="text-gray-500">Environment</p>
            <p className="font-medium">{status?.environment || 'N/A'}</p>
          </div>
          <div>
            <p className="text-gray-500">Last Updated</p>
            <p className="font-medium">{status?.timestamp ? new Date(status.timestamp).toLocaleString() : 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* System Details */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">System Details</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="flex items-start">
            <CpuChipIcon className="h-5 w-5 text-gray-400 mr-2 mt-0.5" />
            <div>
              <p className="text-gray-500">Python Version</p>
              <p className="font-medium text-gray-900">{info?.python_version || 'N/A'}</p>
            </div>
          </div>
          
          <div className="flex items-start">
            <GlobeAltIcon className="h-5 w-5 text-gray-400 mr-2 mt-0.5" />
            <div>
              <p className="text-gray-500">Platform</p>
              <p className="font-medium text-gray-900">{info?.platform || 'N/A'}</p>
            </div>
          </div>
          
          <div className="flex items-start">
            <ServerStackIcon className="h-5 w-5 text-gray-400 mr-2 mt-0.5" />
            <div>
              <p className="text-gray-500">Architecture</p>
              <p className="font-medium text-gray-900">{info?.architecture || 'N/A'}</p>
            </div>
          </div>
          
          <div className="flex items-start">
            <ClockIcon className="h-5 w-5 text-gray-400 mr-2 mt-0.5" />
            <div>
              <p className="text-gray-500">Start Time</p>
              <p className="font-medium text-gray-900">
                {info?.start_time ? new Date(info.start_time).toLocaleString() : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Active Agents/Tasks */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div className="flex items-center mb-4">
          <UserGroupIcon className="h-5 w-5 text-gray-400 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">Active Agents & Tasks</h3>
          <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded-full">
            {activeTasks.length} running
          </span>
        </div>
        
        {activeTasks.length === 0 ? (
          <p className="text-sm text-gray-500">No active agents or tasks running</p>
        ) : (
          <div className="space-y-3">
            {activeTasks.map((task) => (
              <div key={task.task_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    Task: {task.task_id.substring(0, 8)}...
                  </p>
                  <p className="text-xs text-gray-500 truncate max-w-md">
                    {task.input || 'No input'}
                  </p>
                </div>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  task.status === 'running' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {task.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
