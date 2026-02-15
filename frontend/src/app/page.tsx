import ChatInterface from '@/components/ChatInterface'
import AgentPanel from '@/components/AgentPanel'
import ToolTester from '@/components/ToolTester'

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">OMNI</h1>
          <p className="text-sm text-gray-600">Ollama Multi-agent Network Interface</p>
        </div>
      </header>
      
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Chat Interface */}
          <div className="lg:col-span-2">
            <ChatInterface />
          </div>
          
          {/* Sidebar */}
          <div className="space-y-6">
            <AgentPanel />
            <ToolTester />
          </div>
        </div>
      </div>
    </main>
  )
}