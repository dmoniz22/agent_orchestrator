'use client';

import { useState } from 'react';
import { 
  ChatBubbleLeftIcon, 
  UsersIcon, 
  WrenchIcon, 
  CpuChipIcon,
  Cog6ToothIcon,
  Bars3Icon,
  ChevronLeftIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline';

type View = 'chat' | 'agents' | 'tools' | 'models' | 'settings';

interface SidebarProps {
  currentView: View;
  onViewChange: (view: View) => void;
  isExpanded: boolean;
  onToggle: () => void;
}

const navigation = [
  { name: 'Chat', view: 'chat' as View, icon: ChatBubbleLeftIcon },
  { name: 'Agents', view: 'agents' as View, icon: UsersIcon },
  { name: 'Tools', view: 'tools' as View, icon: WrenchIcon },
  { name: 'Models', view: 'models' as View, icon: CpuChipIcon },
  { name: 'Settings', view: 'settings' as View, icon: Cog6ToothIcon },
];

export default function Sidebar({ currentView, onViewChange, isExpanded, onToggle }: SidebarProps) {
  return (
    <div 
      className={`fixed left-0 top-0 h-full bg-white border-r border-gray-200 flex flex-col transition-all duration-300 z-50 ${
        isExpanded ? 'w-64' : 'w-16'
      }`}
    >
      {/* Logo and Toggle */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        {isExpanded ? (
          <>
            <div>
              <h2 className="text-xl font-bold text-gray-900">OMNI</h2>
              <p className="text-xs text-gray-500">Multi-Agent System</p>
            </div>
            <button
              onClick={onToggle}
              className="p-1 rounded-md hover:bg-gray-100 text-gray-600"
              title="Collapse sidebar"
            >
              <ChevronLeftIcon className="h-5 w-5" />
            </button>
          </>
        ) : (
          <button
            onClick={onToggle}
            className="p-1 rounded-md hover:bg-gray-100 text-gray-600 mx-auto"
            title="Expand sidebar"
          >
            <ChevronRightIcon className="h-5 w-5" />
          </button>
        )}
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.view;
          
          return (
            <button
              key={item.name}
              onClick={() => onViewChange(item.view)}
              title={!isExpanded ? item.name : undefined}
              className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              } ${!isExpanded && 'justify-center'}`}
            >
              <Icon className={`h-5 w-5 ${isActive ? 'text-primary-500' : 'text-gray-400'} ${isExpanded && 'mr-3'}`} />
              {isExpanded && <span>{item.name}</span>}
            </button>
          );
        })}
      </nav>
      
      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        {isExpanded ? (
          <p className="text-xs text-gray-500">v0.1.0</p>
        ) : (
          <p className="text-xs text-gray-500 text-center">v0.1</p>
        )}
      </div>
    </div>
  );
}