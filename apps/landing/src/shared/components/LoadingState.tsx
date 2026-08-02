import React from 'react';
import { cn } from '@/lib/utils';

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading workspace benchmarks...',
  className,
}) => {
  return (
    <div className={cn('flex flex-col items-center justify-center p-12 text-center', className)}>
      <div className="w-8 h-8 border-2 border-white/10 border-t-accent rounded-full animate-spin mb-3" />
      <span className="text-xs font-mono tracking-widest text-white/40 uppercase">{message}</span>
    </div>
  );
};

export default LoadingState;
