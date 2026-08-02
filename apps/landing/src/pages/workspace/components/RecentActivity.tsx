/**
 * RecentActivity — append-style timeline from domain/workspace
 */

import { motion } from 'framer-motion';
import {
  Play,
  CheckCircle,
  Upload,
  FileText,
  Cpu,
  Database,
  type LucideIcon,
} from 'lucide-react';
import { fadeUp, stagger } from '@/lib/motion';
import { ACTIVITY_FEED, type ActivityType } from '@/domain/workspace/types';
import { ScrambleSectionTitle } from '@/components/motion';

const ACTIVITY_ICONS: Record<ActivityType, LucideIcon> = {
  evaluation_completed: CheckCircle,
  evaluation_started: Play,
  benchmark_published: Upload,
  report_generated: FileText,
  model_registered: Cpu,
  dataset_imported: Database,
};

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function RecentActivity() {
  return (
    <section className="liquid-glass-card rounded-2xl p-5 border border-white/10 flex flex-col h-full min-h-0">
      <ScrambleSectionTitle text="Activity Timeline" className="text-xs tracking-[0.2em] uppercase text-white/20 mb-4" />

      <motion.div
        variants={stagger(0.05, 0.1)}
        initial="hidden"
        animate="visible"
        className="relative pl-6 border-l border-white/[0.06] space-y-4"
      >
        {ACTIVITY_FEED.slice(0, 6).map((event) => {
          const Icon = ACTIVITY_ICONS[event.type];
          return (
            <motion.div key={event.id} variants={fadeUp} className="relative">
              <div className="absolute -left-[calc(1.5rem+1px)] top-1 w-2.5 h-2.5 rounded-full border border-white/[0.08] flex items-center justify-center" style={{ background: 'var(--color-ink-3)' }}>
                <Icon className="w-2 h-2 text-white/30" />
              </div>
              <div>
                <div className="flex items-baseline justify-between gap-2">
                  <p className="text-sm text-white/70">{event.title}</p>
                  <span className="text-xs text-white/15 shrink-0">
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </div>
                <p className="text-xs text-white/25 mt-0.5 leading-relaxed">
                  {event.description}
                </p>
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </section>
  );
}
