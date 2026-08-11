import { useMemo } from 'react';
import { TextFlippingBoard } from '@/components/ui/text-flipping-board';
import { cn } from '@/lib/utils';

export interface WorkspaceStatusBoardProps {
  isCritical?: boolean;
  isOffline?: boolean;
  providerErrorCount?: number;
  activeBenchmarkCount?: number;
  completedBenchmarkCount?: number;
  modelsCount?: number;
  isNewUser?: boolean;
  
  duration?: number;
  sound?: boolean; // Provided per user request, though unused by Aceternity base
  className?: string;
}

export interface WorkspaceMessage {
  text: string;
  priority: number;
}

function resolveMessage(props: Omit<WorkspaceStatusBoardProps, 'duration' | 'sound' | 'className'>): WorkspaceMessage {
  if (props.isCritical) {
    return { text: "CRITICAL ERROR\nSYSTEM HALTED", priority: 1 };
  }
  if (props.isOffline) {
    return { text: "SYSTEM OFFLINE\nCHECK CONNECTION", priority: 2 };
  }
  if (props.providerErrorCount && props.providerErrorCount > 0) {
    return { text: `PROVIDER ERROR\n${props.providerErrorCount} UNAVAILABLE`, priority: 3 };
  }
  if (props.activeBenchmarkCount && props.activeBenchmarkCount > 0) {
    return { text: `BENCHMARK RUNNING\n${props.activeBenchmarkCount} IN PROGRESS`, priority: 4 };
  }
  if (props.completedBenchmarkCount && props.completedBenchmarkCount > 0) {
    return { text: "BENCHMARK COMPLETE\nSYNC SUCCESSFUL", priority: 5 };
  }
  if (!props.isNewUser && props.modelsCount !== undefined) {
    return { text: `WORKSPACE READY\n${props.modelsCount} MODELS AVAILABLE`, priority: 6 };
  }
  
  return { text: "WELCOME TO ATLAS\nSYSTEM INITIALIZED", priority: 7 };
}

export function WorkspaceStatusBoard({
  isCritical,
  isOffline,
  providerErrorCount,
  activeBenchmarkCount,
  completedBenchmarkCount,
  modelsCount,
  isNewUser,
  duration,
  className,
}: WorkspaceStatusBoardProps) {
  
  const message = useMemo(() => resolveMessage({
    isCritical,
    isOffline,
    providerErrorCount,
    activeBenchmarkCount,
    completedBenchmarkCount,
    modelsCount,
    isNewUser
  }), [
    isCritical,
    isOffline,
    providerErrorCount,
    activeBenchmarkCount,
    completedBenchmarkCount,
    modelsCount,
    isNewUser
  ]);

  return (
    <div className={cn("flex justify-center w-full max-w-4xl mx-auto my-8", className)}>
      <TextFlippingBoard 
        text={message.text}
        duration={duration}
      />
    </div>
  );
}
