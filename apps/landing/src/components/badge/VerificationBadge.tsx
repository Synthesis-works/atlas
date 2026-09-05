import React from 'react';
import { ShieldCheck, Sparkles } from 'lucide-react';

interface VerificationBadgeProps {
  isVerified?: boolean;
  source?: string;
  className?: string;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  isVerified,
  source,
  className = '',
}) => {
  if (isVerified === true) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 ${className}`}
        title="Verified empirical evaluation run"
      >
        <ShieldCheck className="w-3 h-3 text-emerald-400" />
        Verified Run
      </span>
    );
  }

  if (source === 'demo') {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 ${className}`}
        title="Synthetic demo evaluation record"
      >
        <Sparkles className="w-3 h-3 text-amber-400" />
        Demo Data
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-500/10 text-orange-400 border border-orange-500/20 ${className}`}
      title="Execution not yet independently verified"
    >
      <ShieldCheck className="w-3 h-3 text-orange-400" />
      Unverified
    </span>
  );
};

export default VerificationBadge;