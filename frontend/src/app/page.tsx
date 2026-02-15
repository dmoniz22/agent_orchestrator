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
      {/* Left Sidebar */}
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />
      
      {/* Main Content Area */}
      <main className="flex-1 ml-64">
        {/* Header */}
        <header className="bg-white shadow-sm border-b sticky top-0 z-10">
          <div className="px-6 py-4">
            <h1 className="text-2xl font-bold text-gray-900">OMNI</h1>
            <p className="text-sm text-gray-600">Ollama Multi-agent Network Interface</p>
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