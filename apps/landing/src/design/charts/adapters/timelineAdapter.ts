/**
 * Timeline Data Adapter — Converts job execution runs into TimelineStage lists.
 */

import type { TimelineStage } from '../TimelineChart';

export function createTimelineStages(
  currentStage: 'Queued' | 'Preparing' | 'Running' | 'Scoring' | 'Completed',
): TimelineStage[] {
  const STAGES: ('Queued' | 'Preparing' | 'Running' | 'Scoring' | 'Completed')[] = [
    'Queued',
    'Preparing',
    'Running',
    'Scoring',
    'Completed',
  ];

  const currentIdx = STAGES.indexOf(currentStage);

  return STAGES.map((label, idx) => ({
    label,
    status:
      idx < currentIdx
        ? 'completed'
        : idx === currentIdx
        ? 'active'
        : 'queued',
    duration: idx <= currentIdx ? `${((idx + 1) * 2.4).toFixed(1)}s` : undefined,
  }));
}
