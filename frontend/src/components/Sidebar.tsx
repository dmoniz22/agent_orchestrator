'use client';

import { 
  ChatBubbleLeftIcon, 
  UsersIcon, 
  WrenchIcon, 
  CpuChipIcon,
  Cog6ToothIcon 
} from '@heroicons/react/24/outline'

type View = 'chat' | 'agents' | 'tools' | 'models' | 'settings'

interface SidebarProps {
  currentView: View
  onViewChange: (view: View) => void
}

const navigation = [
  { name: 'Chat', view: 'chat' as View, icon: ChatBubbleLeftIcon },
  { name: 'Agents', view: 'agents' as View, icon: UsersIcon },
  { name: 'Tools', view: 'tools' as View, icon: WrenchIcon },
  { name: 'Models', view: 'models' as View, icon: CpuChipIcon },
  { name: 'Settings', view: 'settings' as View, icon: Cog6ToothIcon },
]

export default function Sidebar({ currentView, onViewChange }: SidebarProps) {
  return (
    <div className="fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-xl font-bold text-gray-900">OMNI</h2>
        <p className="text-xs text-gray-500">Multi-Agent System</p>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon
          const isActive = currentView === item.view
          
          return (
            <button
              key={item.name}
              onClick={() => onViewChange(item.view)}
              className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon className={`mr-3 h-5 w-5 ${isActive ? 'text-primary-500' : 'text-gray-400'}`} />
              {item.name}
            </button>
          )
        })}
      </nav>
      
      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">v0.1.0</p>
      </div>
    </div>
  )
}