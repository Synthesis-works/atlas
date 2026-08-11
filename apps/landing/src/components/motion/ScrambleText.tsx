import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { useScramble } from './useScramble';
import type { UseScrambleProps } from './useScramble';
import { useStaggerDelay } from './MotionProvider';
import { MotionTokens } from './tokens';

export interface ScrambleTextProps extends Omit<UseScrambleProps, 'delay'> {
  as?: React.ElementType;
  className?: string;
  delay?: number;
  children?: React.ReactNode;
}

export function ScrambleText({
  text,
  as: Component = 'span',
  className,
  delay: manualDelay,
  children,
  ...scrambleOptions
}: ScrambleTextProps) {
  const ref = useRef<HTMLElement>(null);
  const staggerDelay = useStaggerDelay(manualDelay);

  const { prefersReducedMotion } = useScramble(ref, {
    text,
    delay: staggerDelay,
    ...scrambleOptions,
  });

  const MotionComponent = motion.create(Component as React.ForwardRefExoticComponent<any>);

  return (
    <MotionComponent
      initial={{ opacity: 0, y: prefersReducedMotion ? 0 : MotionTokens.spacing.yOffset }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        duration: MotionTokens.durations.fade, 
        delay: staggerDelay / 1000 // framer-motion delay is in seconds
      }}
      className={className}
    >
      {prefersReducedMotion ? (
        <span ref={ref} className="inline-block min-h-[1em]">
          {text}
        </span>
      ) : (
        <span ref={ref} className="inline-block min-h-[1em]" />
      )}
      {!prefersReducedMotion && <span className="sr-only">{text}</span>}
      {children}
    </MotionComponent>
  );
}
