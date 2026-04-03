'use client';

import { useState, useEffect } from 'react';
import { ServerStackIcon, ClockIcon, CpuChipIcon, GlobeAltIcon } from '@heroicons/react/24/outline';

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

export default function SystemInfo() {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSystemInfo();
  }, []);

  const loadSystemInfo = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const [infoRes, statusRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/system/info`),
        fetch(`${apiUrl}/api/v1/system/status`),
      ]);
      
      if (!infoRes.ok || !statusRes.ok) {
        throw new Error('Failed to fetch system info');
      }
      
      const [infoData, statusData] = await Promise.all([
        infoRes.json(),
        statusRes.json(),
      ]);
      
      setInfo(infoData);
      setStatus(statusData);
    } catch (err) {
      setError('Failed to load system information');
    } finally {
      setLoading(false);
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
    </div>
  );
}
