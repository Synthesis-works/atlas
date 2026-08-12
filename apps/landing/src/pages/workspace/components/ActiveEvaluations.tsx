/**
 * ActiveEvaluations — dynamic execution runs powered by getDashboardSummary
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { fadeUp, stagger } from '@/lib/motion';
import { Card, Badge } from '@/design/primitives';
import { VerificationBadge } from '@/components/badge/VerificationBadge';
import { ScrambleSectionTitle } from '@/components/motion';

export interface ActiveExecutionItem {
  id: string;
  model: string;
  benchmark: string;
  status: string;
  progress: number;
  is_verified?: boolean;
  source?: string;
}

export function ActiveEvaluations({ items = [], title = "Recent & Active Evaluations" }: { items?: ActiveExecutionItem[]; title?: string }) {
  const activeRuns = items.slice(0, 4);

  return (
    <section>
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <ScrambleSectionTitle text={title} className="text-xs tracking-[0.18em] uppercase text-white/35" />
          <p className="text-xs text-white/30 mt-1">{items.length} verified executions & active pipeline jobs</p>
        </div>

        <Link
          to="/dashboard/evaluations"
          className="shrink-0 text-xs text-accent/80 hover:text-accent transition-colors"
        >
          View queue
        </Link>
      </div>

      <motion.div
        variants={stagger(0.06, 0.1)}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 gap-3"
      >
        {activeRuns.map((run) => {
          const isCompleted = run.status === 'Completed';
          const isFailed = run.status === 'Failed' || run.status === 'Cancelled';
          const isActive = !isCompleted && !isFailed;

          const Icon = isCompleted ? CheckCircle2 : (isFailed ? XCircle : Loader2);
          const iconColor = isCompleted ? 'text-success' : (isFailed ? 'text-error' : 'text-accent');

          return (
            <motion.div key={run.id} variants={fadeUp}>
              <Card className="!rounded-lg !p-4 h-full">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <Icon
                      className={`w-4 h-4 mt-0.5 shrink-0 ${iconColor} ${isActive ? 'animate-spin' : ''}`}
                    />
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium text-white truncate">
                          {run.model} on {run.benchmark}
                        </p>
                        <VerificationBadge isVerified={run.is_verified} source={run.source} />
                      </div>
                      <p className="text-xs text-white/20 font-mono mt-0.5">
                        {run.id}
                      </p>
                    </div>
                  </div>
                  <Badge variant={isActive ? 'accent' : 'default'}>
                    {run.status}
                  </Badge>
                </div>


                {isActive && (
                  <div className="mt-3">
                    <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-accent/60 transition-all duration-700"
                        style={{ width: `${run.progress}%` }}
                      />
                    </div>
                    <p className="text-[11px] text-white/30 mt-1.5">{run.progress}% complete</p>
                  </div>
                )}
              </Card>
            </motion.div>
          );
        })}
      </motion.div>
    </section>
  );
}
