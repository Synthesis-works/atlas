import { useId, useEffect } from "react";
import { Check, Server, Activity, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { useProviderCatalog } from "../../hooks/useProviderCatalog";

export function AtlasProviderGrid({ catalog }: { catalog: ReturnType<typeof useProviderCatalog> }) {
  const { cards, selectedIds, expandedId, handleSelect, handleToggleExpand, handleOpenPreview } = catalog;
  const layoutIdPrefix = useId();

  const activeCard = cards.find(c => c.id === expandedId) || null;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (expandedId) handleToggleExpand(expandedId);
      }
    }

    if (activeCard) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeCard, expandedId, handleToggleExpand]);

  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case 'operational': return <div className="w-2 h-2 rounded-full bg-emerald-400" />;
      case 'degraded': return <div className="w-2 h-2 rounded-full bg-yellow-400" />;
      case 'outage': return <div className="w-2 h-2 rounded-full bg-red-400" />;
      default: return <div className="w-2 h-2 rounded-full bg-slate-400" />;
    }
  };

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
        {cards.map((card) => {
          const isSelected = selectedIds.includes(card.id);

          return (
            <motion.div
              layoutId={`${layoutIdPrefix}-${card.id}`}
              key={card.id}
              onClick={() => handleToggleExpand(card.id)}
              className={`
                group relative flex flex-col p-4 rounded-xl cursor-pointer
                transition-all duration-300
                ${isSelected ? 'bg-indigo-500/10 border-indigo-500/50' : 'bg-white/[0.02] hover:bg-white/[0.04] border-white/10'}
                border backdrop-blur-md
              `}
            >
              {/* Checkbox Overlay */}
              <div 
                className={`absolute top-4 right-4 z-10 transition-opacity duration-200 ${isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelect(card.id, true);
                }}
              >
                <div className={`w-5 h-5 rounded flex items-center justify-center border transition-colors ${
                  isSelected ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-white/20 hover:border-white/40'
                }`}>
                  {isSelected && <Check className="w-3.5 h-3.5" />}
                </div>
              </div>

              {/* Header */}
              <div className="flex items-start justify-between mb-4 pr-6">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <StatusIcon status={card.status} />
                    <h3 className="font-medium text-white group-hover:text-indigo-300 transition-colors">
                      {card.name}
                    </h3>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-white/60 border border-white/10 capitalize">
                    {card.tier}
                  </span>
                </div>
              </div>

              <p className="text-sm text-white/50 line-clamp-2 mb-6 flex-1">
                {card.description}
              </p>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                <div className="flex items-center gap-1.5 text-white/40">
                  <Server className="w-3.5 h-3.5" />
                  <span>{card.modelsCount} Models</span>
                </div>
                <div className="flex items-center gap-1.5 text-white/40">
                  <Activity className="w-3.5 h-3.5" />
                  <span>{card.averageLatencyMs}ms Avg</span>
                </div>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-1.5 mt-auto">
                {card.tags.map(tag => (
                  <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-white/50 border border-white/5">
                    {tag}
                  </span>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Expanded Overlay */}
      <AnimatePresence>
        {activeCard ? (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
              onClick={() => handleToggleExpand(activeCard.id)}
            />
            <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none p-4">
              <motion.div
                layoutId={`${layoutIdPrefix}-${activeCard.id}`}
                className="w-full max-w-lg bg-[#0F1117] border border-white/10 rounded-2xl overflow-hidden shadow-2xl pointer-events-auto flex flex-col"
              >
                <div className="p-6">
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <StatusIcon status={activeCard.status} />
                        <h2 className="text-2xl font-bold text-white">{activeCard.name}</h2>
                      </div>
                      <span className="text-sm px-2.5 py-1 rounded-full bg-white/5 text-white/60 border border-white/10 capitalize">
                        {activeCard.tier} Tier
                      </span>
                    </div>
                  </div>

                  <p className="text-white/70 mb-8 leading-relaxed">
                    {activeCard.description}
                  </p>

                  <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <div className="text-sm text-white/50 mb-1">Available Models</div>
                      <div className="text-2xl font-medium text-white">{activeCard.modelsCount}</div>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <div className="text-sm text-white/50 mb-1">Global Uptime</div>
                      <div className="text-2xl font-medium text-white">{activeCard.uptimePercentage}%</div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-8">
                    {activeCard.tags.map(tag => (
                      <span key={tag} className="text-xs px-2.5 py-1 rounded bg-white/5 text-white/60 border border-white/10">
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="flex gap-3">
                    <button 
                      onClick={() => {
                        handleToggleExpand(activeCard.id);
                        handleOpenPreview(activeCard.id);
                      }}
                      className="flex-1 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors font-medium flex items-center justify-center gap-2"
                    >
                      View Provider Details <ArrowRight className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => handleToggleExpand(activeCard.id)}
                      className="px-6 py-2.5 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors border border-white/10"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </motion.div>
            </div>
          </>
        ) : null}
      </AnimatePresence>
    </>
  );
}
