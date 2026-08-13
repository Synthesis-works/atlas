import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';

type AsyncState = 'idle' | 'loading' | 'success' | 'error';

export function AtlasBulkActions({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  const { selectedIds, handleClearSelection } = catalog;
  const [actionState, setActionState] = useState<AsyncState>('idle');
  const [activeAction, setActiveAction] = useState<string | null>(null);
  
  if (selectedIds.length === 0) return null;

  const simulateAction = (actionName: string) => {
    setActiveAction(actionName);
    setActionState('loading');
    
    // Simulate async network request
    setTimeout(() => {
      setActionState('success');
      
      // Reset after showing success briefly
      setTimeout(() => {
        setActionState('idle');
        setActiveAction(null);
        handleClearSelection();
      }, 1500);
    }, 1000);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="h-14 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex items-center px-4 justify-between"
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-indigo-400 font-medium">
          <span className="w-5 h-5 rounded-md bg-indigo-500/20 flex items-center justify-center text-xs">
            {selectedIds.length}
          </span>
          <span>Datasets Selected</span>
        </div>
        
        <div className="w-px h-6 bg-indigo-500/20"></div>
        
        <div className="flex items-center gap-2">
          <button 
            disabled={actionState !== 'idle' || selectedIds.length !== 2}
            onClick={() => { /* Comparison panel handles this, but we could trigger it */ }}
            className="px-3 py-1.5 rounded-lg text-sm transition-colors text-indigo-300 hover:text-indigo-100 hover:bg-indigo-500/20 disabled:opacity-50 disabled:hover:bg-transparent"
          >
            Compare
          </button>
          <button 
            disabled={actionState !== 'idle'}
            onClick={() => simulateAction('Validate')}
            className="px-3 py-1.5 rounded-lg text-sm transition-colors text-indigo-300 hover:text-indigo-100 hover:bg-indigo-500/20 disabled:opacity-50 disabled:hover:bg-transparent"
          >
            {activeAction === 'Validate' && actionState === 'loading' ? 'Validating...' : 'Validate'}
          </button>
          <button 
            disabled={actionState !== 'idle'}
            onClick={() => simulateAction('Export')}
            className="px-3 py-1.5 rounded-lg text-sm transition-colors text-indigo-300 hover:text-indigo-100 hover:bg-indigo-500/20 disabled:opacity-50 disabled:hover:bg-transparent"
          >
            {activeAction === 'Export' && actionState === 'loading' ? 'Exporting...' : 'Export'}
          </button>
          <button 
            disabled={actionState !== 'idle'}
            onClick={() => simulateAction('Generate Embeddings')}
            className="px-3 py-1.5 rounded-lg text-sm transition-colors text-indigo-300 hover:text-indigo-100 hover:bg-indigo-500/20 disabled:opacity-50 disabled:hover:bg-transparent"
          >
            {activeAction === 'Generate Embeddings' && actionState === 'loading' ? 'Generating...' : 'Generate Embeddings'}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <AnimatePresence>
          {actionState === 'success' && (
            <motion.span 
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="text-emerald-400 text-sm flex items-center gap-1"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg>
              {activeAction} Successful
            </motion.span>
          )}
        </AnimatePresence>
        
        <button 
          onClick={handleClearSelection}
          className="text-indigo-400/50 hover:text-indigo-300 transition-colors"
        >
          ✕
        </button>
      </div>
    </motion.div>
  );
}
