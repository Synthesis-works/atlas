import { motion, AnimatePresence } from "framer-motion";
import { useId, useRef, useEffect } from "react";
import { useOutsideClick } from "@/hooks/use-outside-click";
import { useBenchmarkCatalog } from '../../hooks/useBenchmarkCatalog';

export const CloseIcon = () => {
  return (
    <motion.svg
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.05 } }}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4 text-white"
    >
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M18 6l-12 12" />
      <path d="M6 6l12 12" />
    </motion.svg>
  );
};

export function AtlasBenchmarkGrid({ catalog }: { catalog: ReturnType<typeof useBenchmarkCatalog> }) {
  const { cards, expandedId, handleToggleExpand, selectedIds, handleSelect } = catalog;
  const id = useId();
  const ref = useRef<any>(null);
  
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

  useOutsideClick(ref, () => {
    if (expandedId) handleToggleExpand(expandedId);
  });

  return (
    <>
      <AnimatePresence>
        {activeCard && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm h-full w-full z-50"
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {activeCard ? (
          <div className="fixed inset-0 grid place-items-center z-[100] p-4 md:p-10">
            <motion.button
              key={`button-${activeCard.id}-${id}`}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.05 } }}
              className="flex absolute top-4 right-4 items-center justify-center bg-white/10 hover:bg-white/20 border border-white/20 rounded-full h-8 w-8 transition-colors"
              onClick={() => handleToggleExpand(activeCard.id)}
            >
              <CloseIcon />
            </motion.button>
            <motion.div
              layoutId={`card-${activeCard.id}-${id}`}
              ref={ref}
              className="w-full max-w-[800px] h-full md:h-fit md:max-h-[90%] flex flex-col bg-neutral-900 border border-white/10 sm:rounded-3xl overflow-hidden shadow-2xl"
            >
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex justify-between items-start p-6 border-b border-white/10">
                  <div className="flex flex-col gap-1">
                    <motion.h3
                      layoutId={`title-${activeCard.id}-${id}`}
                      className="font-medium text-white text-2xl"
                    >
                      {activeCard.name}
                    </motion.h3>
                    <motion.p
                      layoutId={`description-${activeCard.id}-${id}`}
                      className="text-white/60 text-base flex gap-3 items-center"
                    >
                      <span className="capitalize">{activeCard.category}</span>
                      <span>•</span>
                      <span className="capitalize">{activeCard.difficulty}</span>
                      <span>•</span>
                      <span className="text-emerald-400">{activeCard.status}</span>
                    </motion.p>
                  </div>

                  <motion.button
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => catalog.handleOpenPreview(activeCard.id)}
                    className="px-6 py-2.5 text-sm rounded-xl font-medium bg-white text-black hover:bg-neutral-200 transition-colors"
                  >
                    Open Preview
                  </motion.button>
                </div>
                <div className="p-6 relative flex-1 overflow-y-auto">
                  <motion.div
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-neutral-400 text-sm flex flex-col gap-6"
                  >
                    <p>{activeCard.description}</p>
                    <div className="grid grid-cols-3 gap-4 p-4 rounded-xl bg-white/5 border border-white/5">
                      <div className="flex flex-col gap-1">
                        <span className="text-xs uppercase tracking-wider text-white/40">Tasks</span>
                        <span className="text-white">{activeCard.tasksCountFormatted}</span>
                      </div>
                      <div className="flex flex-col gap-1">
                        <span className="text-xs uppercase tracking-wider text-white/40">Score</span>
                        <span className="text-white">{activeCard.verificationScore}</span>
                      </div>
                      <div className="flex flex-col gap-1">
                        <span className="text-xs uppercase tracking-wider text-white/40">Runtime</span>
                        <span className="text-white">{activeCard.estimatedRuntime}</span>
                      </div>
                    </div>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>
      
      <ul className="w-full grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] items-start gap-6">
        {catalog.cards.map((card: any) => {
          const isSelected = selectedIds.includes(card.id);
          const handleClick = (e: React.MouseEvent) => {
            if (e.detail === 2) {
              catalog.handleOpenPreview(card.id);
            } else if (e.shiftKey) {
              catalog.handleRangeSelect(card.id, catalog.rawVisibleIds);
            } else {
              catalog.handleSelect(card.id, e.ctrlKey || e.metaKey);
            }
          };

          return (
            <motion.div
              layoutId={`card-${card.id}-${id}`}
              key={card.id}
              onClick={handleClick}
              className={`flex flex-col bg-white/5 hover:bg-white/10 border transition-colors rounded-2xl overflow-hidden group select-none ${isSelected ? 'border-indigo-500 bg-indigo-500/10' : 'border-white/10'}`}
            >
              <div className="relative w-full p-5 pb-0">
                <div className="absolute top-3 left-3 z-10" onClick={(e) => e.stopPropagation()}>
                   <input 
                     type="checkbox" 
                     className="w-5 h-5 rounded border-white/20 bg-black/50 text-indigo-500 focus:ring-indigo-500 cursor-pointer"
                     checked={isSelected}
                     onChange={() => handleSelect(card.id, true)}
                   />
                </div>
                
                <div className="absolute top-3 right-3 z-10 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                  <button 
                    onClick={() => handleToggleExpand(card.id)}
                    className="p-1.5 rounded-lg bg-black/50 text-white/60 hover:text-white border border-white/10 backdrop-blur-md"
                    title="Quick Expand"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
                  </button>
                </div>
              </div>
              
              <div className="flex flex-col p-5 cursor-pointer mt-4">
                <motion.h3
                  layoutId={`title-${card.id}-${id}`}
                  className="font-medium text-white text-lg mb-1 truncate"
                >
                  {card.name}
                </motion.h3>
                <motion.p
                  layoutId={`description-${card.id}-${id}`}
                  className="text-white/50 text-sm flex items-center justify-between"
                >
                  <span className="capitalize">{card.category} • {card.difficulty}</span>
                  <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${card.status === 'Ready' || card.status === 'Running' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                    {card.status}
                  </span>
                </motion.p>
              </div>
            </motion.div>
          );
        })}
      </ul>
    </>
  );
}
