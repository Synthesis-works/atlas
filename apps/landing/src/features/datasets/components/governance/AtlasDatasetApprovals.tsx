import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasAvatar } from '@/components/atlas/AtlasAvatar';
import { motion } from 'framer-motion';

export function AtlasDatasetApprovals({ governance }: { governance: ReturnType<typeof useDatasetGovernance> }) {
  const { approvals } = governance;

  return (
    <AtlasInsightCard title="Approval Workflow">
      <div className="flex flex-col gap-6 relative">
        {/* Connecting Line */}
        <div className="absolute top-4 bottom-4 left-[19px] w-0.5 bg-white/5 z-0" />
        
        {approvals.steps.map((step, index) => {
          const isPending = !step.isCompleted && !step.isActive;
          
          return (
            <motion.div 
              key={step.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`relative z-10 flex gap-4 ${isPending ? 'opacity-50' : 'opacity-100'}`}
            >
              {/* Node indicator */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border-4 border-neutral-900 ${
                step.isCompleted ? 'bg-indigo-500 text-white' : 
                step.isActive ? 'bg-amber-500 text-white shadow-[0_0_15px_rgba(245,158,11,0.5)]' : 
                'bg-white/10 text-white/40'
              }`}>
                {step.isCompleted ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>
                ) : (
                  <span className="text-sm font-medium">{index + 1}</span>
                )}
              </div>

              {/* Content */}
              <div className="flex-1 flex flex-col gap-2 pt-1 border border-white/5 bg-white/5 p-4 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className={`font-medium ${step.isActive ? 'text-white' : 'text-white/70'}`}>
                    {step.status}
                  </span>
                  {step.timestamp && (
                    <span className="text-xs text-white/40">{step.timestamp}</span>
                  )}
                </div>
                
                {step.reason && (
                  <p className="text-sm text-white/50">{step.reason}</p>
                )}
                
                {step.approver && (
                  <div className="flex items-center gap-2 mt-2">
                    <AtlasAvatar src={step.approver.avatarUrl} initials={step.approver.name.charAt(0)} size="sm" />
                    <span className="text-xs text-white/60">{step.approver.name}</span>
                  </div>
                )}

                {step.isActive && (
                  <div className="flex gap-2 mt-4 pt-4 border-t border-white/10">
                    <button className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 rounded-lg text-sm font-medium transition-colors">
                      Approve
                    </button>
                    <button className="px-3 py-1.5 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg text-sm font-medium transition-colors">
                      Request Changes
                    </button>
                    <button className="px-3 py-1.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg text-sm font-medium transition-colors">
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </AtlasInsightCard>
  );
}
