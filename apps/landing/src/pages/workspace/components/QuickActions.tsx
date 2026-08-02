/**
 * QuickActions — workspace shortcuts from domain/workspace
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Play,
  Database,
  FileText,
  BarChart3,
  FolderKanban,
  Cpu,
  type LucideIcon,
} from 'lucide-react';
import { fadeUp, stagger } from '@/lib/motion';
import { Card } from '@/design/primitives';
import { ScrambleSectionTitle } from '@/components/motion';
import { QUICK_ACTIONS } from '@/domain/workspace/types';

const ICON_MAP: Record<string, LucideIcon> = {
  Play,
  Database,
  FileText,
  BarChart3,
  FolderKanban,
  Cpu,
};

export function QuickActions() {
  return (
    <section className="liquid-glass-card rounded-2xl p-5 border border-white/10 h-full flex flex-col">
      <ScrambleSectionTitle text="Quick Actions" className="text-xs tracking-[0.2em] uppercase text-white/20 mb-4" />

      <motion.div
        variants={stagger(0.06, 0.1)}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 gap-3"
      >
        {QUICK_ACTIONS.map((action) => {
          const Icon = ICON_MAP[action.icon] ?? Play;
          return (
            <motion.div key={action.id} variants={fadeUp}>
              <Link to={action.href}>
                <Card hover className="flex items-start gap-3 !p-4 group cursor-pointer h-full">
                  <div className="liquid-glass rounded-lg p-2 shrink-0">
                    <Icon className="w-4 h-4 text-accent/70" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white group-hover:text-accent-hover transition-colors">
                      {action.label}
                    </p>
                    <p className="text-xs text-white/25 mt-0.5 leading-relaxed">
                      {action.description}
                    </p>
                  </div>
                </Card>
              </Link>
            </motion.div>
          );
        })}
      </motion.div>
    </section>
  );
}
