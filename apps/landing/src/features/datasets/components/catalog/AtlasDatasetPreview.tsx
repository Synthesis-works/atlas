import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';
import { AtlasDatasetGovernance } from '../governance/AtlasDatasetGovernance';
import { AtlasDatasetCollaboration } from '../governance/AtlasDatasetCollaboration';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';

export function AtlasDatasetPreview({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  const { previewModel, handleClosePreview } = catalog;
  const activeTab = useWorkspaceInteractionStore(s => s.workspaces['datasets']?.view.activePreviewTab || 'Overview');
  const setActiveTab = useWorkspaceInteractionStore(s => s.setActivePreviewTab);
  const setScrollPosition = useWorkspaceInteractionStore(s => s.setScrollPosition);
  const savedScroll = useWorkspaceInteractionStore(s => s.workspaces['datasets']?.navigation.scrollPosition || 0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const tabs = [
    'Overview', 'Metadata', 'Relationships', 'Benchmarks', 'Models', 'Activity', 'Governance', 'Collaboration', 'Atlas Intelligence'
  ];

  // Restore scroll position
  useEffect(() => {
    if (scrollRef.current && savedScroll > 0) {
      scrollRef.current.scrollTop = savedScroll;
    }
  }, [previewModel?.id]); // Only restore on initial open of this dataset

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
          // Debounce this in a real app
          setScrollPosition('datasets', (e.target as HTMLDivElement).scrollTop);
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
          <img src={previewModel.thumbnailUrl} alt="" className="w-16 h-16 rounded-xl object-cover shrink-0" />
          <div className="flex flex-col gap-1 w-full">
            <div className="flex flex-col">
              <h3 className="text-white text-xl font-medium leading-tight">{previewModel.name}</h3>
              <p className="text-white/50 text-sm">Created {previewModel.createdAt}</p>
            </div>
            
            {/* Dense Metadata Grid */}
            <div className="grid grid-cols-3 gap-4 mt-4 bg-white/5 p-3 rounded-lg border border-white/10 w-full">
              <div className="flex flex-col gap-2">
                <h4 className="text-[10px] text-white/30 uppercase tracking-widest font-semibold">Identity</h4>
                <div className="flex flex-col gap-1">
                  <span className="text-xs text-white/50">Owner: <span className="text-white/80">Data Eng</span></span>
                  <span className="text-xs text-white/50">Tags: <span className="text-white/80">#vision, #prod</span></span>
                  <span className="text-xs text-white/50">Schema: <span className="text-white/80">v2.4</span></span>
                </div>
              </div>
              <div className="flex flex-col gap-2 border-l border-white/10 pl-4">
                <h4 className="text-[10px] text-white/30 uppercase tracking-widest font-semibold">Quality</h4>
                <div className="flex flex-col gap-1">
                  <span className="text-xs text-white/50">Health: <span className="text-emerald-400">{previewModel.healthScore}%</span></span>
                  <span className="text-xs text-white/50">Validation: <span className="text-white/80">Passed</span></span>
                  <span className="text-xs text-white/50">Freshness: <span className="text-white/80">2h ago</span></span>
                </div>
              </div>
              <div className="flex flex-col gap-2 border-l border-white/10 pl-4">
                <h4 className="text-[10px] text-white/30 uppercase tracking-widest font-semibold">Storage</h4>
                <div className="flex flex-col gap-1">
                  <span className="text-xs text-white/50">Size: <span className="text-white/80">{previewModel.sizeFormatted}</span></span>
                  <span className="text-xs text-white/50">Records: <span className="text-white/80">{previewModel.samplesFormatted}</span></span>
                  <span className="text-xs text-white/50">Lineage: <span className="text-white/80">Depth 3</span></span>
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
            onClick={() => setActiveTab('datasets', tab)}
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
              </div>
            )}

            {activeTab.toLowerCase() === 'governance' && (
              <AtlasDatasetGovernance datasetId={previewModel.id} />
            )}

            {activeTab.toLowerCase() === 'collaboration' && (
              <AtlasDatasetCollaboration datasetId={previewModel.id} />
            )}

            {activeTab.toLowerCase() !== 'overview' && activeTab.toLowerCase() !== 'governance' && activeTab.toLowerCase() !== 'collaboration' && (
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
          Open Dataset
        </button>
        <button className="px-4 bg-white/5 hover:bg-white/10 text-white py-2 rounded-xl border border-white/10 transition-colors">
          Compare
        </button>
      </div>
    </motion.div>
  );
}
