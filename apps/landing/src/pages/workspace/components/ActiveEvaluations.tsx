/**
 * ActiveEvaluations — in-flight evaluation runs from domain/evaluations
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { fadeUp, stagger } from '@/lib/motion';
import { Card, Badge } from '@/design/primitives';
import { useEvaluations } from '@/features/evaluations/hooks/useEvaluations';
import { ScrambleSectionTitle } from '@/components/motion';
import type { EvaluationStatus } from '@/domain/evaluations/types';

const STATUS_ICON: Record<EvaluationStatus, typeof Loader2> = {
  Queued: Clock,
  Loading: Loader2,
  Preparing: Loader2,
  Running: Loader2,
  Scoring: Loader2,
  Aggregating: Loader2,
  Reporting: Loader2,
  Completed: CheckCircle2,
  Failed: XCircle,
  Cancelled: XCircle,
  Paused: Clock,
  Retrying: Loader2,
};

const STATUS_COLOR: Record<EvaluationStatus, string> = {
  Queued: 'text-white/30',
  Loading: 'text-accent',
  Preparing: 'text-accent',
  Running: 'text-accent',
  Scoring: 'text-accent',
  Aggregating: 'text-accent',
  Reporting: 'text-accent',
  Completed: 'text-success',
  Failed: 'text-error',
  Cancelled: 'text-orange-400',
  Paused: 'text-amber-400',
  Retrying: 'text-sky-400',
};

export function ActiveEvaluations() {
  const { activeEvaluations } = useEvaluations();
  const active = activeEvaluations.filter((e) => e.status !== 'Completed' && e.status !== 'Failed');
  const runs = active.slice(0, 4);

  return (
    <section>
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <ScrambleSectionTitle text="Active Evaluations" className="text-xs tracking-[0.18em] uppercase text-white/35" />
          <p className="text-xs text-white/30 mt-1">{active.length} jobs currently moving through the pipeline</p>
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
        {runs.map((run) => {
          const Icon = STATUS_ICON[run.status];
          const isActive = run.status === 'Running' || run.status === 'Scoring' || run.status === 'Loading';

          return (
            <motion.div key={run.id} variants={fadeUp}>
              <Card className="!rounded-lg !p-4 h-full">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <Icon
                      className={`w-4 h-4 mt-0.5 shrink-0 ${STATUS_COLOR[run.status]} ${isActive ? 'animate-spin' : ''}`}
                    />
                    <div>
                      <p className="text-sm font-medium text-white truncate">
                        {run.model} on {run.benchmark}
                      </p>
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
