import React from 'react';
import { cn } from '@/lib/utils';

interface ProvenanceBadgeProps {
  source?: string | null;
  isVerified?: boolean | null;
  label?: string;
  className?: string;
}

/**
 * Honest provenance indicator. Renders ONLY when the backend explicitly reports
 * demo or unverified data (source="demo" / is_verified=false). Unknown provenance
 * renders nothing so real verified runs are never mislabeled.
 */
export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  source,
  isVerified,
  label,
  className,
}) => {
  if (source === 'demo') {
    return (
      <span
        title="Backend reports this data as a demo/sample run (source=demo)"
        className={cn(
          'px-2 py-0.5 rounded text-[10px] font-mono font-medium border shrink-0',
          'bg-amber-500/15 text-amber-300 border-amber-500/30',
          className
        )}
      >
        {label ?? 'Demo'}
      </span>
    );
  }

  if (isVerified === false) {
    return (
      <span
        title="Backend reports this data is not independently verified (is_verified=false)"
        className={cn(
          'px-2 py-0.5 rounded text-[10px] font-mono font-medium border shrink-0',
          'bg-orange-500/15 text-orange-300 border-orange-500/30',
          className
        )}
      >
        {label ?? 'Unverified'}
      </span>
    );
  }

  return null;
};

export default ProvenanceBadge;