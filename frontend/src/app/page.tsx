'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar'
import ChatInterface from '@/components/ChatInterface'
import AgentManager from '@/components/AgentManager'
import ToolManager from '@/components/ToolManager'
import ModelManager from '@/components/ModelManager'
import SettingsPanel from '@/components/SettingsPanel'
import CrewManager from '@/components/CrewManager'
import SystemInfo from '@/components/SystemInfo'

type View = 'chat' | 'agents' | 'tools' | 'models' | 'settings' | 'crews' | 'system'

export default function Home() {
  const [currentView, setCurrentView] = useState<View>('chat')
  const [sidebarExpanded, setSidebarExpanded] = useState(true)

  const renderContent = () => {
    switch (currentView) {
      case 'chat':
        return <ChatInterface />
      case 'agents':
        return <AgentManager />
      case 'tools':
        return <ToolManager />
      case 'models':
        return <ModelManager />
      case 'settings':
        return <SettingsPanel />
      case 'crews':
        return <CrewManager />
      case 'system':
        return <SystemInfo />
      default:
        return <ChatInterface />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* Collapsible Sidebar - Fixed Position */}
      <Sidebar 
        currentView={currentView} 
        onViewChange={setCurrentView}
        isExpanded={sidebarExpanded}
        onToggle={() => setSidebarExpanded(!sidebarExpanded)}
      />
      
      {/* Main Content Area */}
      <div 
        className="transition-all duration-300 min-h-screen"
        style={{
          marginLeft: sidebarExpanded ? '256px' : '64px',
          width: sidebarExpanded ? 'calc(100% - 256px)' : 'calc(100% - 64px)',
        }}
      >
        {/* Header */}
        <header className="bg-white shadow-sm border-b sticky top-0 z-10">
          <div className="px-4 py-4 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">OMNI</h1>
              <p className="text-sm text-gray-600">Ollama Multi-agent Network Interface</p>
            </div>
            <button
              onClick={() => setSidebarExpanded(!sidebarExpanded)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700"
            >
              {sidebarExpanded ? 'Hide Sidebar' : 'Show Sidebar'}
            </button>
          </div>
        </header>
        
        {/* Content */}
        <div className="p-4 w-full max-w-full box-border">
          {renderContent()}
        </div>
      </div>
    </div>
  )
}
