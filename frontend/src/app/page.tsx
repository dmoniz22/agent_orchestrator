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
    <div className="min-h-screen bg-gray-50 flex">
      {/* Collapsible Sidebar */}
      <Sidebar 
        currentView={currentView} 
        onViewChange={setCurrentView}
        isExpanded={sidebarExpanded}
        onToggle={() => setSidebarExpanded(!sidebarExpanded)}
      />
      
      {/* Main Content Area - adjusts margin based on sidebar width */}
      <main 
        className={`flex-1 transition-all duration-300 ${
          sidebarExpanded ? 'ml-64' : 'ml-16'
        }`}
      >
        {/* Header */}
        <header className="bg-white shadow-sm border-b sticky top-0 z-10">
          <div className="px-6 py-4 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">OMNI</h1>
              <p className="text-sm text-gray-600">Ollama Multi-agent Network Interface</p>
            </div>
            <button
              onClick={() => setSidebarExpanded(!sidebarExpanded)}
              className="p-2 rounded-md hover:bg-gray-100 text-gray-600 lg:hidden"
              title={sidebarExpanded ? "Hide sidebar" : "Show sidebar"}
            >
              {sidebarExpanded ? (
                <span className="text-sm">Hide Sidebar</span>
              ) : (
                <span className="text-sm">Show Sidebar</span>
              )}
            </button>
          </div>
        </header>
        
        {/* Content */}
        <div className="p-6">
          {renderContent()}
        </div>
      </main>
    </div>
  )
}