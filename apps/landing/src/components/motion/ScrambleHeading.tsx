import { ScrambleText } from './ScrambleText';
import type { ScrambleTextProps } from './ScrambleText';
import { MotionTokens } from './tokens';

export function ScrambleHeading({
  className = "text-2xl font-semibold tracking-tight text-white",
  children,
  ...props
}: Omit<ScrambleTextProps, 'duration'>) {
  return (
    <ScrambleText
      as="h1"
      duration={MotionTokens.durations.heading}
      className={className}
      {...props}
    >
      {children}
    </ScrambleText>
  );
}
