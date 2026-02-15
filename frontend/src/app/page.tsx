'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar'
import ChatInterface from '@/components/ChatInterface'
import AgentManager from '@/components/AgentManager'
import ToolManager from '@/components/ToolManager'
import ModelManager from '@/components/ModelManager'
import SettingsPanel from '@/components/SettingsPanel'

type View = 'chat' | 'agents' | 'tools' | 'models' | 'settings'

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
      default:
        return <ChatInterface />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Collapsible Sidebar */}
      <Sidebar 
        currentView={currentView} 
        onViewChange={setCurrentView}
        isExpanded={sidebarExpanded}
        onToggle={() => setSidebarExpanded(!sidebarExpanded)}
      />
      
      {/* Main Content Area - adjusts margin and width based on sidebar */}
      <main 
        className={`transition-all duration-300 min-h-screen ${
          sidebarExpanded ? 'ml-64' : 'ml-16'
        }`}
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
        
        {/* Content - with overflow handling */}
        <div className="p-4 w-full overflow-x-hidden">
          {renderContent()}
        </div>
      </main>
    </div>
  )
}