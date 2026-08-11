import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasAvatar } from '@/components/atlas/AtlasAvatar';
import { motion, AnimatePresence } from 'framer-motion';

export function AtlasDatasetActivity({ governance }: { governance: ReturnType<typeof useDatasetGovernance> }) {
  const { activityTimeline, activityFilter, setActivityFilter } = governance;

  return (
    <AtlasInsightCard title="Activity Timeline">
      <div className="flex items-center gap-2 mb-6 overflow-x-auto no-scrollbar pb-2">
        {['All', 'Today', 'Week', 'Month'].map(dateRange => (
          <button 
            key={dateRange}
            onClick={() => setActivityFilter({ ...activityFilter, dateRange: dateRange as any })}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              activityFilter.dateRange === dateRange ? 'bg-indigo-500 text-white' : 'bg-white/5 text-white/60 hover:text-white hover:bg-white/10'
            }`}
          >
            {dateRange}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-6 relative">
        <div className="absolute top-4 bottom-4 left-[19px] w-0.5 bg-white/5 z-0" />
        
        <AnimatePresence>
          {activityTimeline.map((item) => (
            <motion.div 
              key={item.id}
              layout
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative z-10 flex gap-4"
            >
              <div className="w-10 h-10 shrink-0 bg-neutral-900 flex items-center justify-center">
                <AtlasAvatar src={item.user.avatarUrl} initials={item.user.name.charAt(0)} size="md" />
              </div>

              <div className="flex-1 flex flex-col gap-2 pt-1 border border-white/5 bg-white/5 p-4 rounded-xl">
                <div className="flex justify-between items-start">
                  <p className="text-sm text-white/90">
                    <span className="font-medium mr-1">{item.user.name}</span>
                    <span className="text-white/60">{item.action}</span>
                  </p>
                  <span className="text-xs text-white/40 whitespace-nowrap ml-4">{item.timestamp}</span>
                </div>
                
                {item.metadata && (
                  <div className="mt-2 p-3 bg-black/30 rounded-lg border border-white/5 text-xs font-mono text-white/50">
                    {Object.entries(item.metadata).map(([k, v]) => (
                      <div key={k}><span className="text-white/30">{k}:</span> {v}</div>
                    ))}
                  </div>
                )}
                
                <div className="mt-2 flex items-center gap-3">
                  <span className={`text-[10px] uppercase tracking-wider font-medium px-2 py-0.5 rounded ${
                    item.status === 'Success' ? 'bg-emerald-500/10 text-emerald-400' :
                    item.status === 'Warning' ? 'bg-amber-500/10 text-amber-400' :
                    item.status === 'Failed' ? 'bg-red-500/10 text-red-400' :
                    'bg-white/10 text-white/60'
                  }`}>
                    {item.status}
                  </span>
                  <button className="text-xs text-indigo-400 hover:text-indigo-300">View Details</button>
                </div>
              </div>
            </motion.div>
          ))}
          
          {activityTimeline.length === 0 && (
             <div className="py-8 text-center text-white/40 text-sm">
               No activity for this date range.
             </div>
          )}
        </AnimatePresence>
      </div>
    </AtlasInsightCard>
  );
}
