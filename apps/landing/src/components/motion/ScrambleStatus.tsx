import { ScrambleText } from './ScrambleText';
import type { ScrambleTextProps } from './ScrambleText';
import { MotionTokens } from './tokens';

export function ScrambleStatus({
  className = "text-xs font-semibold text-white",
  children,
  ...props
}: Omit<ScrambleTextProps, 'duration'>) {
  return (
    <ScrambleText
      as="span"
      duration={MotionTokens.durations.status}
      className={className}
      {...props}
    >
      {children}
    </ScrambleText>
  );
}
