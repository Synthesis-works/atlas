import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { motion, AnimatePresence } from 'framer-motion';

export function AtlasDatasetLineage({ governance }: { governance: ReturnType<typeof useDatasetGovernance> }) {
  const { lineage, lineageState, handleNodeExpand, handleNodeSelect } = governance;

  // Recursive tree rendering
  const renderNode = (nodeId: string, depth: number = 0) => {
    const node = lineage.nodes[nodeId];
    if (!node) return null;

    const isExpanded = lineageState.expandedNodes.includes(nodeId);
    const isSelected = lineageState.selectedNodeId === nodeId;
    const hasChildren = node.childrenIds.length > 0;

    return (
      <div key={nodeId} className="flex flex-col">
        <div 
          className="flex items-center gap-2 py-2"
          style={{ paddingLeft: `${depth * 24}px` }}
        >
          {hasChildren ? (
            <button 
              onClick={() => handleNodeExpand(nodeId)}
              className="w-5 h-5 flex items-center justify-center text-white/40 hover:text-white transition-colors bg-white/5 rounded"
            >
              <motion.span
                animate={{ rotate: isExpanded ? 90 : 0 }}
                transition={{ duration: 0.2 }}
              >
                ▶
              </motion.span>
            </button>
          ) : (
            <div className="w-5 h-5" /> // spacer
          )}
          
          <button 
            onClick={() => handleNodeSelect(nodeId)}
            className={`flex-1 flex flex-col items-start px-3 py-2 rounded-lg border text-left transition-colors ${
              isSelected ? 'bg-indigo-500/20 border-indigo-500/50' : 'bg-white/5 border-white/5 hover:border-white/20'
            }`}
          >
            <div className="flex items-center gap-2 w-full justify-between">
              <span className="text-sm font-medium text-white">{node.name}</span>
              <span className="text-[10px] uppercase tracking-wider text-white/40 bg-black/50 px-2 py-0.5 rounded">
                {node.type}
              </span>
            </div>
          </button>
        </div>

        <AnimatePresence>
          {isExpanded && hasChildren && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              {node.childrenIds.map(childId => renderNode(childId, depth + 1))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  return (
    <AtlasInsightCard title="Dataset Lineage">
      <div className="flex flex-col bg-black/20 rounded-xl p-4 min-h-[300px] border border-white/5">
        <div className="text-xs text-white/40 uppercase tracking-wider mb-4 border-b border-white/10 pb-2">
          Dependency Tree
        </div>
        {renderNode(lineage.rootId)}
      </div>
    </AtlasInsightCard>
  );
}
