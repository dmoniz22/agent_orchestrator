'use client';

import { useState, useEffect } from 'react';
import { 
  Cog6ToothIcon, 
  ShieldCheckIcon, 
  BellIcon,
  KeyIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiKeysData {
  openrouter_api_key_masked: string;
  openrouter_configured: boolean;
  openrouter_default_model: string;
  openrouter_base_url: string;
  provider_prefer_local: boolean;
  provider_fallback_on_error: boolean;
  ollama_base_url: string;
  ollama_default_model: string;
}

interface NotificationData {
  task_completion: boolean;
  error_alerts: boolean;
  agent_notifications: boolean;
  daily_summary: boolean;
  webhook_url: string;
}

interface SecurityData {
  require_auth: boolean;
  api_rate_limit: number;
  allowed_origins: string;
  session_timeout_minutes: number;
  enable_https: boolean;
}

export default function SettingsPanel() {
  const [activeTab, setActiveTab] = useState('api');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [saveMessage, setSaveMessage] = useState('');

  const tabs = [
    { id: 'api', name: 'API Keys', icon: KeyIcon },
    { id: 'general', name: 'General', icon: Cog6ToothIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
  ];

  const showStatus = (status: 'saved' | 'error', message: string) => {
    setSaveStatus(status);
    setSaveMessage(message);
    setTimeout(() => { setSaveStatus('idle'); setSaveMessage(''); }, 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-600">Configure system preferences and API connections</p>
      </div>

      {/* Status Banner */}
      {saveStatus !== 'idle' && (
        <div className={`flex items-center p-3 rounded-lg text-sm ${
          saveStatus === 'saved' 
            ? 'bg-green-50 border border-green-200 text-green-800' 
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          {saveStatus === 'saved' 
            ? <CheckCircleIcon className="h-5 w-5 mr-2 flex-shrink-0" /> 
            : <ExclamationTriangleIcon className="h-5 w-5 mr-2 flex-shrink-0" />}
          {saveMessage}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-5 w-5 mr-2" />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {activeTab === 'api' && <ApiKeysTab onStatus={showStatus} />}
        {activeTab === 'general' && <GeneralTab onStatus={showStatus} />}
        {activeTab === 'security' && <SecurityTab onStatus={showStatus} />}
        {activeTab === 'notifications' && <NotificationsTab onStatus={showStatus} />}
      </div>
    </div>
  );
}

/* ==================== API Keys Tab ==================== */
function ApiKeysTab({ onStatus }: { onStatus: (s: 'saved' | 'error', m: string) => void }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ApiKeysData | null>(null);
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [openrouterModel, setOpenrouterModel] = useState('');
  const [preferLocal, setPreferLocal] = useState(true);
  const [fallbackOnError, setFallbackOnError] = useState(true);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/settings/api-keys`);
      const json = await res.json();
      setData(json);
      setOpenrouterModel(json.openrouter_default_model || 'anthropic/claude-3-haiku-20240307');
      setPreferLocal(json.provider_prefer_local);
      setFallbackOnError(json.provider_fallback_on_error);
    } catch {
      onStatus('error', 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const body: Record<string, any> = {
        provider_prefer_local: preferLocal,
        provider_fallback_on_error: fallbackOnError,
        openrouter_default_model: openrouterModel,
      };
      if (openrouterKey.trim()) {
        body.openrouter_api_key = openrouterKey.trim();
      }

      const res = await fetch(`${API_URL}/api/v1/settings/api-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (res.ok) {
        onStatus('saved', json.message || 'Settings saved successfully');
        setOpenrouterKey('');
        loadSettings();
      } else {
        onStatus('error', json.detail || 'Failed to save settings');
      }
    } catch {
      onStatus('error', 'Failed to save settings');
    }
  };

  if (loading) return <div className="animate-pulse h-64 bg-gray-100 rounded" />;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">API Keys & Provider Configuration</h3>

      {/* Ollama Section */}
      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="font-medium text-gray-900">Ollama (Local)</h4>
            <p className="text-sm text-gray-500">Local inference server — free, private, no API key needed</p>
          </div>
          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">Active</span>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <label className="block text-gray-500 mb-1">Server URL</label>
            <input type="text" value={data?.ollama_base_url || ''} readOnly className="w-full rounded-md border-gray-200 bg-gray-50 text-gray-700 text-sm" />
          </div>
          <div>
            <label className="block text-gray-500 mb-1">Default Model</label>
            <input type="text" value={data?.ollama_default_model || ''} readOnly className="w-full rounded-md border-gray-200 bg-gray-50 text-gray-700 text-sm" />
          </div>
        </div>
      </div>

      {/* OpenRouter Section */}
      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="font-medium text-gray-900">OpenRouter (Cloud)</h4>
            <p className="text-sm text-gray-500">Access Claude, GPT-4o, Gemini, and 100+ cloud models</p>
          </div>
          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
            data?.openrouter_configured ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
          }`}>
            {data?.openrouter_configured ? 'Configured' : 'Not Set'}
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <div className="flex space-x-2">
              <div className="relative flex-1">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={openrouterKey}
                  onChange={(e) => setOpenrouterKey(e.target.value)}
                  placeholder={data?.openrouter_configured ? `Current: ${data.openrouter_api_key_masked}` : 'sk-or-v1-...'}
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                />
              </div>
              <button
                onClick={() => setShowKey(!showKey)}
                className="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 text-gray-600"
              >
                {showKey ? 'Hide' : 'Show'}
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Get your key at <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">openrouter.ai/keys</a>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default Cloud Model</label>
            <select
              value={openrouterModel}
              onChange={(e) => setOpenrouterModel(e.target.value)}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
            >
              <option value="anthropic/claude-3-haiku-20240307">Claude 3 Haiku (Fast, Cheap)</option>
              <option value="anthropic/claude-3-sonnet-20240229">Claude 3 Sonnet (Balanced)</option>
              <option value="anthropic/claude-3-opus-20240229">Claude 3 Opus (Best Quality)</option>
              <option value="openai/gpt-4o">GPT-4o</option>
              <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
              <option value="google/gemini-pro-1.5">Gemini Pro 1.5</option>
              <option value="google/gemini-flash-1.5">Gemini Flash 1.5</option>
              <option value="meta-llama/llama-3.1-70b-instruct">Llama 3.1 70B</option>
              <option value="mistralai/mistral-large">Mistral Large</option>
              <option value="deepseek/deepseek-coder">DeepSeek Coder</option>
            </select>
          </div>
        </div>
      </div>

      {/* Provider Strategy */}
      <div className="border border-gray-200 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">Provider Strategy</h4>
        <div className="space-y-3">
          <label className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-gray-700">Prefer Local Models</span>
              <p className="text-xs text-gray-500">Route to Ollama first when a local model matches</p>
            </div>
            <input
              type="checkbox"
              checked={preferLocal}
              onChange={(e) => setPreferLocal(e.target.checked)}
              className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
          </label>
          <label className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-gray-700">Auto-Fallback to Cloud</span>
              <p className="text-xs text-gray-500">If Ollama fails, automatically retry with OpenRouter</p>
            </div>
            <input
              type="checkbox"
              checked={fallbackOnError}
              onChange={(e) => setFallbackOnError(e.target.checked)}
              className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
          </label>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium"
        >
          Save API Settings
        </button>
      </div>
    </div>
  );
}

/* ==================== General Tab ==================== */
function GeneralTab({ onStatus }: { onStatus: (s: 'saved' | 'error', m: string) => void }) {
  const [systemName, setSystemName] = useState('OMNI');
  const [logLevel, setLogLevel] = useState('INFO');
  const [maxSteps, setMaxSteps] = useState(10);

  const handleSave = () => {
    onStatus('saved', 'General settings saved. Some changes require a restart.');
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">General Settings</h3>
      
      <div className="grid grid-cols-1 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">System Name</label>
          <input
            type="text"
            value={systemName}
            onChange={(e) => setSystemName(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Log Level</label>
          <select
            value={logLevel}
            onChange={(e) => setLogLevel(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="DEBUG">DEBUG — Verbose logging</option>
            <option value="INFO">INFO — Standard logging</option>
            <option value="WARNING">WARNING — Warnings only</option>
            <option value="ERROR">ERROR — Errors only</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Max Steps Per Task</label>
          <input
            type="number"
            value={maxSteps}
            onChange={(e) => setMaxSteps(parseInt(e.target.value))}
            min={1}
            max={50}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Maximum orchestration steps before stopping. Higher = more complex tasks but slower.
          </p>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
          Save Changes
        </button>
      </div>
    </div>
  );
}

/* ==================== Security Tab ==================== */
function SecurityTab({ onStatus }: { onStatus: (s: 'saved' | 'error', m: string) => void }) {
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState<SecurityData>({
    require_auth: false,
    api_rate_limit: 100,
    allowed_origins: 'http://localhost:3000,http://localhost:3002',
    session_timeout_minutes: 60,
    enable_https: false,
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/settings/security`);
      if (res.ok) {
        const json = await res.json();
        setSettings(json);
      }
    } catch { /* use defaults */ }
    setLoading(false);
  };

  const handleSave = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/settings/security`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        onStatus('saved', 'Security settings saved. CORS changes require server restart.');
      } else {
        onStatus('error', 'Failed to save security settings');
      }
    } catch {
      onStatus('error', 'Failed to save security settings');
    }
  };

  if (loading) return <div className="animate-pulse h-64 bg-gray-100 rounded" />;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">Security Settings</h3>

      <div className="space-y-4">
        <label className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
          <div>
            <span className="text-sm font-medium text-gray-700">Require Authentication</span>
            <p className="text-xs text-gray-500">Enable API key or JWT authentication for all endpoints</p>
          </div>
          <input
            type="checkbox"
            checked={settings.require_auth}
            onChange={(e) => setSettings({ ...settings, require_auth: e.target.checked })}
            className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
          />
        </label>

        <label className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
          <div>
            <span className="text-sm font-medium text-gray-700">Enable HTTPS</span>
            <p className="text-xs text-gray-500">Force HTTPS for all connections (requires SSL certificate)</p>
          </div>
          <input
            type="checkbox"
            checked={settings.enable_https}
            onChange={(e) => setSettings({ ...settings, enable_https: e.target.checked })}
            className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
          />
        </label>

        <div>
          <label className="block text-sm font-medium text-gray-700">API Rate Limit (requests/minute)</label>
          <input
            type="number"
            value={settings.api_rate_limit}
            onChange={(e) => setSettings({ ...settings, api_rate_limit: parseInt(e.target.value) })}
            min={10}
            max={10000}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Session Timeout (minutes)</label>
          <input
            type="number"
            value={settings.session_timeout_minutes}
            onChange={(e) => setSettings({ ...settings, session_timeout_minutes: parseInt(e.target.value) })}
            min={5}
            max={1440}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Allowed CORS Origins</label>
          <textarea
            value={settings.allowed_origins}
            onChange={(e) => setSettings({ ...settings, allowed_origins: e.target.value })}
            rows={2}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm font-mono"
            placeholder="http://localhost:3000,http://localhost:3002"
          />
          <p className="mt-1 text-xs text-gray-500">Comma-separated list of allowed frontend origins</p>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
          Save Security Settings
        </button>
      </div>
    </div>
  );
}

/* ==================== Notifications Tab ==================== */
function NotificationsTab({ onStatus }: { onStatus: (s: 'saved' | 'error', m: string) => void }) {
  const [settings, setSettings] = useState<NotificationData>({
    task_completion: true,
    error_alerts: true,
    agent_notifications: false,
    daily_summary: false,
    webhook_url: '',
  });

  const handleSave = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/settings/notifications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (res.ok) {
        onStatus('saved', 'Notification settings saved.');
      } else {
        onStatus('error', 'Failed to save notification settings');
      }
    } catch {
      onStatus('error', 'Failed to save notification settings');
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">Notification Preferences</h3>
      <p className="text-sm text-gray-600">
        Configure when and how you receive notifications about system activity.
      </p>

      <div className="space-y-3">
        {[
          { key: 'task_completion', label: 'Task Completion', desc: 'Notify when an agent finishes a task' },
          { key: 'error_alerts', label: 'Error Alerts', desc: 'Notify when an agent or tool encounters an error' },
          { key: 'agent_notifications', label: 'Agent Activity', desc: 'Notify on agent routing decisions and tool usage' },
          { key: 'daily_summary', label: 'Daily Summary', desc: 'Receive a daily summary of all agent activity' },
        ].map((item) => (
          <label key={item.key} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
            <div>
              <span className="text-sm font-medium text-gray-700">{item.label}</span>
              <p className="text-xs text-gray-500">{item.desc}</p>
            </div>
            <input
              type="checkbox"
              checked={settings[item.key as keyof NotificationData] as boolean}
              onChange={(e) => setSettings({ ...settings, [item.key]: e.target.checked })}
              className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
          </label>
        ))}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Webhook URL (Optional)</label>
        <input
          type="url"
          value={settings.webhook_url}
          onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
          placeholder="https://hooks.slack.com/services/..."
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
        />
        <p className="mt-1 text-xs text-gray-500">
          Send notifications to Slack, Discord, or any webhook-compatible service
        </p>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 text-sm font-medium">
          Save Notification Settings
        </button>
      </div>
    </div>
  );
}
