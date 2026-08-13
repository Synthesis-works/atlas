import { ScrambleText } from './ScrambleText';
import type { ScrambleTextProps } from './ScrambleText';
import { MotionTokens } from './tokens';

export function ScrambleSectionTitle({
  className = "text-xs tracking-[0.2em] uppercase text-white/20 mb-4",
  children,
  ...props
}: Omit<ScrambleTextProps, 'duration'>) {
  return (
    <ScrambleText
      as="h2"
      duration={MotionTokens.durations.sectionTitle}
      className={className}
      {...props}
    >
      {children}
    </ScrambleText>
  );
}
