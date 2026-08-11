import React from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'The registry awaits its first benchmark',
  description = 'Scientific evaluation begins with a single reproducible experiment.',
  action,
  className,
}) => {
  return (
    <div className={cn('flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-dashed border-white/10 bg-white/[0.01] w-full max-w-[480px] mx-auto', className)}>
      <div className="w-12 h-12 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-6">
        <Sparkles className="w-6 h-6 text-accent" />
      </div>
      <h3 className="text-base font-semibold text-white tracking-tight mb-3">{title}</h3>
      <p className="text-xs text-white/40 leading-relaxed mb-6">{description}</p>
      {action}
    </div>
  );
};

export default EmptyState;
