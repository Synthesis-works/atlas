import { useState } from 'react';
import { motion } from 'framer-motion';

export interface AtlasTab {
  id: string;
  label: string;
  content: React.ReactNode;
}

interface AtlasTabsProps {
  tabs: AtlasTab[];
  defaultTabId?: string;
  onChange?: (tabId: string) => void;
  className?: string;
}

export function AtlasTabs({ tabs, defaultTabId, onChange, className = '' }: AtlasTabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTabId || tabs[0]?.id);

  const handleTabClick = (id: string) => {
    setActiveTab(id);
    if (onChange) onChange(id);
  };

  return (
    <div className={`flex flex-col w-full h-full ${className}`}>
      {/* Tab List */}
      <div className="flex items-center overflow-x-auto border-b border-white/10 px-6 no-scrollbar hide-scrollbar shrink-0">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => handleTabClick(tab.id)}
            className={`relative whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id 
                ? 'text-indigo-400' 
                : 'text-white/50 hover:text-white'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <motion.div
                layoutId="atlas-tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500"
                initial={false}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Tab Panel */}
      <div className="flex-1 overflow-y-auto relative">
        {tabs.map(tab => (
           <div
             key={tab.id}
             className={`absolute inset-0 p-6 ${activeTab === tab.id ? 'opacity-100 z-10 pointer-events-auto' : 'opacity-0 z-0 pointer-events-none'}`}
             style={{ transition: 'opacity 0.2s ease-in-out' }} // Simple CSS fade per rules (No bouncing)
           >
             {tab.content}
           </div>
        ))}
      </div>
    </div>
  );
}
