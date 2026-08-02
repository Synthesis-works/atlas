import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useBenchmarkCatalog } from '../../hooks/useBenchmarkCatalog';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';

export function AtlasBenchmarkPreview({ catalog }: { catalog: ReturnType<typeof useBenchmarkCatalog> }) {
  const { previewModel, handleClosePreview } = catalog;
  const activeTab = useWorkspaceInteractionStore(s => s.workspaces['benchmarks']?.view.activePreviewTab || 'Overview');
  const setActiveTab = useWorkspaceInteractionStore(s => s.setActivePreviewTab);
  const setScrollPosition = useWorkspaceInteractionStore(s => s.setScrollPosition);
  const savedScroll = useWorkspaceInteractionStore(s => s.workspaces['benchmarks']?.navigation.scrollPosition || 0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const tabs = [
    'Overview', 'Metrics', 'Tasks', 'Artifacts', 'Settings'
  ];

  // Restore scroll position
  useEffect(() => {
    if (scrollRef.current && savedScroll > 0) {
      scrollRef.current.scrollTop = savedScroll;
    }
  }, [previewModel?.id]); // Only restore on initial open of this model

  if (!previewModel) return null;

  return (
    <motion.div 
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 100, opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="w-full shrink-0 lg:w-[520px] lg:min-w-[420px] lg:max-w-[640px] h-[calc(100vh-120px)] sticky top-[100px] border border-white/10 rounded-2xl bg-black/80 backdrop-blur-xl flex flex-col overflow-hidden shadow-2xl z-40"
    >
      {/* Scrollable Body */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto relative"
        onScroll={(e) => {
          setScrollPosition('benchmarks', (e.target as HTMLDivElement).scrollTop);
        }}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10 relative">
          <button 
            onClick={handleClosePreview}
            className="absolute top-6 right-6 text-white/40 hover:text-white transition-colors"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6l-12 12M6 6l12 12"/></svg>
          </button>
          <div className="flex gap-4 items-start pr-8">
            <div className="flex flex-col gap-1 w-full">
              <div className="flex flex-col">
                <h3 className="text-white text-xl font-medium leading-tight">{previewModel.name} <span className="text-sm text-white/40 ml-2">v{previewModel.version}</span></h3>
                <p className="text-white/50 text-sm capitalize">{previewModel.category} • {previewModel.difficulty}</p>
              </div>
              
              {/* Dense Metadata Grid */}
              <div className="grid grid-cols-3 gap-4 mt-4 bg-white/5 p-3 rounded-lg border border-white/10 w-full">
                <div className="flex flex-col gap-2">
                  <h4 className="text-[10px] text-white/30 uppercase tracking-widest font-semibold">Identity</h4>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-white/50">Author: <span className="text-white/80">{previewModel.author}</span></span>
                    <span className="text-xs text-white/50">License: <span className="text-white/80">{previewModel.license}</span></span>
                  </div>
                </div>
                <div className="flex flex-col gap-2 border-l border-white/10 pl-4">
                  <h4 className="text-[10px] text-white/30 uppercase tracking-widest font-semibold">Size</h4>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-white/50">Tasks: <span className="text-white/80">{previewModel.tasksCountFormatted}</span></span>
                    <span className="text-xs text-white/50">Runtime: <span className="text-white/80">{previewModel.estimatedRuntime}</span></span>
                  </div>
                </div>
                <div className="flex flex-col gap-2 border-l border-white/10 pl-4">
                  <h4 className="text-[10px] text-white/30 uppercase tracking-widest font-semibold">Health</h4>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-white/50">Score: <span className="text-emerald-400">{previewModel.verificationScore}%</span></span>
                    <span className="text-xs text-white/50">Status: <span className="text-white/80">{previewModel.status}</span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="sticky top-0 z-10 bg-black/80 backdrop-blur-md flex items-center overflow-x-auto border-b border-white/10 px-6 no-scrollbar hide-scrollbar">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab('benchmarks', tab)}
              className={`whitespace-nowrap px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab.toLowerCase() === tab.toLowerCase()
                  ? 'border-indigo-500 text-indigo-400' 
                  : 'border-transparent text-white/50 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="p-6 text-sm text-white/70">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.15 }}
            >
              {activeTab.toLowerCase() === 'overview' && (
                <div className="flex flex-col gap-6">
                  <div>
                    <h4 className="text-white font-medium mb-2">Description</h4>
                    <p>{previewModel.description}</p>
                  </div>
                  <div>
                    <h4 className="text-white font-medium mb-2">Details</h4>
                    <p>{previewModel.details}</p>
                  </div>
                  <div>
                    <h4 className="text-white font-medium mb-2">Tags</h4>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {previewModel.tags.map(tag => (
                        <span key={tag} className="px-2 py-1 rounded bg-white/10 text-xs">{tag}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab.toLowerCase() !== 'overview' && (
                <div className="h-40 flex items-center justify-center text-white/30 border border-white/5 border-dashed rounded-xl">
                  {activeTab} coming soon
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

      </div>

      {/* Actions */}
      <div className="shrink-0 p-6 border-t border-white/10 flex gap-3 bg-black/80 backdrop-blur-md">
        <button className="flex-1 bg-indigo-500 hover:bg-indigo-600 text-white py-2 rounded-xl font-medium transition-colors">
          Run Benchmark
        </button>
        <button className="px-4 bg-white/5 hover:bg-white/10 text-white py-2 rounded-xl border border-white/10 transition-colors">
          Compare
        </button>
      </div>
    </motion.div>
  );
}
