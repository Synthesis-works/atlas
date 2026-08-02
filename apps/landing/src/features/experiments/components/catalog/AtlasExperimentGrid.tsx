import { useId, useEffect } from "react";
import { Check, Clock, Activity, ArrowRight, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { useExperimentCatalog } from "../../hooks/useExperimentCatalog";
import type { MockExperimentStatus } from "../../mocks/mock";

export function AtlasExperimentGrid({ catalog }: { catalog: ReturnType<typeof useExperimentCatalog> }) {
  const { rows, selectedIds, previewId, handleSelect, handleOpenPreview, handleClosePreview } = catalog;
  const layoutIdPrefix = useId();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (previewId) handleClosePreview();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [previewId, handleClosePreview]);

  const StatusIcon = ({ status }: { status: MockExperimentStatus }) => {
    switch (status) {
      case 'Queued': return <div className="w-2 h-2 rounded-full bg-white/40" />;
      case 'Running': return <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />;
      case 'Completed': return <div className="w-2 h-2 rounded-full bg-emerald-400" />;
      case 'Failed': return <div className="w-2 h-2 rounded-full bg-red-400" />;
      case 'Cancelled': return <div className="w-2 h-2 rounded-full bg-slate-400" />;
      default: return null;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
      {rows.map((row) => {
        const isSelected = selectedIds.includes(row.id);
        const isFailed = row.status === 'Failed';
        const isCompleted = row.status === 'Completed';

        let barColor = 'bg-indigo-500';
        if (isFailed) barColor = 'bg-red-500';
        if (isCompleted) barColor = 'bg-emerald-500';
        if (row.status === 'Queued') barColor = 'bg-white/20';

        return (
          <motion.div
            layoutId={`${layoutIdPrefix}-${row.id}`}
            key={row.id}
            onClick={() => handleOpenPreview(row.id)}
            className={`
              group relative flex flex-col p-4 rounded-xl cursor-pointer
              transition-all duration-300
              ${isSelected ? 'bg-indigo-500/10 border-indigo-500/50' : 'bg-white/[0.02] hover:bg-white/[0.04] border-white/10'}
              border backdrop-blur-md overflow-hidden
            `}
          >
            {/* Top progress bar for active runs */}
            {row.status === 'Running' && (
              <div className="absolute top-0 left-0 right-0 h-1 bg-white/5">
                <div 
                  className="h-full bg-indigo-500 relative overflow-hidden" 
                  style={{ width: `${row.progressPercentage}%` }}
                >
                  <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_1.5s_infinite]" style={{ transform: 'skewX(-20deg) translateX(-150%)' }} />
                </div>
              </div>
            )}

            {/* Checkbox Overlay */}
            <div 
              className={`absolute top-4 right-4 z-10 transition-opacity duration-200 ${isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
              onClick={(e) => {
                e.stopPropagation();
                handleSelect(row.id, true);
              }}
            >
              <div className={`w-5 h-5 rounded flex items-center justify-center border transition-colors ${
                isSelected ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-white/20 hover:border-white/40'
              }`}>
                {isSelected && <Check className="w-3.5 h-3.5" />}
              </div>
            </div>

            {/* Header */}
            <div className="flex items-start justify-between mb-4 pr-6 pt-1">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <StatusIcon status={row.status} />
                  <h3 className="font-medium text-white group-hover:text-indigo-300 transition-colors truncate max-w-[200px]">
                    {row.name}
                  </h3>
                </div>
                <span className="text-xs text-white/50">{row.status}</span>
              </div>
            </div>

            {/* Stage Progress (Mid section) */}
            <div className="mb-4 flex-1">
              <div className="flex justify-between items-center text-xs mb-1.5">
                <span className={`font-medium ${isFailed ? 'text-red-400' : row.status === 'Running' ? 'text-indigo-300' : 'text-white/60'}`}>
                  {row.currentStage}
                </span>
                <span className="text-white/50">{row.progressPercentage}%</span>
              </div>
              <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden mb-1.5">
                <div 
                  className={`h-full ${barColor} transition-all duration-500`}
                  style={{ width: `${Math.max(row.progressPercentage, 2)}%` }}
                />
              </div>
              <div className="text-[10px] text-white/40 flex justify-between">
                <span>{row.stageCountText}</span>
                {row.etaText && <span>{row.etaText}</span>}
              </div>
            </div>

            {/* Footer Metrics */}
            <div className="flex items-center justify-between mt-auto pt-4 border-t border-white/5">
              <div className="flex items-center gap-1.5 text-xs text-white/40">
                <Clock className="w-3.5 h-3.5" />
                <span>{row.durationText}</span>
              </div>
              <div className="flex gap-1">
                {row.tags.slice(0, 2).map(tag => (
                  <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/50 border border-white/5 capitalize">
                    {tag}
                  </span>
                ))}
                {row.tags.length > 2 && <span className="text-[10px] text-white/40">+{row.tags.length - 2}</span>}
              </div>
            </div>
          </motion.div>
        );
      })}
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes shimmer {
          100% { transform: skewX(-20deg) translateX(200%); }
        }
      `}} />
    </div>
  );
}
