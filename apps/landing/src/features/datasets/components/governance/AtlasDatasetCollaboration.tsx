import { useDatasetGovernance } from '../../hooks/useDatasetGovernance';
import { AtlasAvatar } from '@/components/atlas/AtlasAvatar';
import { motion, AnimatePresence } from 'framer-motion';

export function AtlasDatasetCollaboration({ datasetId }: { datasetId: string }) {
  const { collaborationComments } = useDatasetGovernance(datasetId);

  return (
    <div className="flex flex-col gap-6 h-full">
      <div className="flex items-center gap-4 border-b border-white/10 pb-4">
        <h3 className="text-white text-lg font-medium">Recent Discussions</h3>
        <span className="bg-indigo-500/10 text-indigo-400 text-xs px-2 py-0.5 rounded-full">
          {collaborationComments.length} active
        </span>
      </div>

      <div className="flex flex-col gap-4 overflow-y-auto pr-2 pb-24">
        <AnimatePresence>
          {collaborationComments.map(comment => (
            <motion.div 
              key={comment.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-4 p-4 rounded-xl bg-white/5 border border-white/5 group hover:border-white/10 transition-colors"
            >
              <AtlasAvatar src={comment.user.avatarUrl} initials={comment.user.name.charAt(0)} size="md" />
              <div className="flex flex-col gap-2 flex-1">
                <div className="flex justify-between items-center">
                  <span className="text-white text-sm font-medium">{comment.user.name}</span>
                  <span className="text-white/40 text-xs">{comment.timestamp}</span>
                </div>
                <p className="text-white/70 text-sm">{comment.content}</p>
                <div className="flex gap-4 mt-2">
                  <button className="text-xs text-white/40 hover:text-white transition-colors">Reply</button>
                  <button className="text-xs text-white/40 hover:text-white transition-colors">Resolve</button>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Input area mockup */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-neutral-900 border-t border-white/10">
        <div className="flex gap-3">
          <AtlasAvatar initials="Me" size="md" />
          <div className="flex-1 relative">
            <input 
              type="text" 
              placeholder="Write a comment or type @ to mention someone..."
              className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500"
            />
            <button className="absolute right-2 top-1.5 p-1 text-indigo-400 hover:text-indigo-300">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
