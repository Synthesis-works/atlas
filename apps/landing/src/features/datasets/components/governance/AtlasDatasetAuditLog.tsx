import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasAvatar } from '@/components/atlas/AtlasAvatar';
import { AtlasBadge } from '@/components/atlas/AtlasBadge';
import { motion, AnimatePresence } from 'framer-motion';

export function AtlasDatasetAuditLog({ governance }: { governance: ReturnType<typeof useDatasetGovernance> }) {
  const { auditLogs, auditState, setAuditSearch, setAuditActionFilter } = governance;

  return (
    <AtlasInsightCard title="Audit Log">
      {/* Filters & Search */}
      <div className="flex items-center gap-4 mb-4 border-b border-white/10 pb-4">
        <input 
          type="text" 
          placeholder="Search audit events..." 
          value={auditState.search}
          onChange={(e) => setAuditSearch(e.target.value)}
          className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500"
        />
        <select 
          value={auditState.actionFilter}
          onChange={(e) => setAuditActionFilter(e.target.value)}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Actions</option>
          <option value="Created">Created</option>
          <option value="Updated">Updated</option>
          <option value="Permission Changed">Permission Changed</option>
        </select>
      </div>

      <div className="flex flex-col gap-2 max-h-[400px] overflow-y-auto pr-2">
        <AnimatePresence>
          {auditLogs.map((log) => (
            <motion.div 
              key={log.id}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex flex-col p-4 rounded-xl bg-white/5 border border-white/5 gap-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <AtlasAvatar src={log.user.avatarUrl} initials={log.user.name.charAt(0)} size="sm" />
                  <span className="text-white text-sm font-medium">{log.user.name}</span>
                </div>
                <span className="text-white/40 text-xs">{log.timestamp}</span>
              </div>
              
              <div className="flex items-center gap-3">
                <AtlasBadge variant={log.action === 'Updated' ? 'info' : 'default'}>
                  {log.action}
                </AtlasBadge>
                {log.reason && (
                  <span className="text-white/70 text-sm truncate">{log.reason}</span>
                )}
              </div>
              
              {/* Diff (mock placeholder for before/after) */}
              {(log.beforeSnapshot || log.afterSnapshot) && (
                <div className="grid grid-cols-2 gap-4 mt-2 p-3 bg-black/40 rounded-lg border border-white/5 text-xs font-mono text-white/50">
                  <div className="flex flex-col text-red-400">
                    <span className="mb-1 uppercase tracking-wider text-[10px] text-white/30">Before</span>
                    {log.beforeSnapshot}
                  </div>
                  <div className="flex flex-col text-emerald-400">
                    <span className="mb-1 uppercase tracking-wider text-[10px] text-white/30">After</span>
                    {log.afterSnapshot}
                  </div>
                </div>
              )}
            </motion.div>
          ))}
          {auditLogs.length === 0 && (
            <div className="py-8 text-center text-white/40 text-sm">
              No audit logs match your search.
            </div>
          )}
        </AnimatePresence>
      </div>
    </AtlasInsightCard>
  );
}
