import React, { useRef } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { MotionTokens } from '@/design/tokens';

export interface AnimatedSectionProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export function AnimatedSection({ children, className = '', delay = 0 }: AnimatedSectionProps) {
  const prefersReducedMotion = useReducedMotion();
  const ref = useRef<HTMLElement>(null);

  if (prefersReducedMotion) {
    return <section className={className}>{children}</section>;
  }

  return (
    <motion.section
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ 
        duration: MotionTokens.durations.section / 1000, 
        delay: delay / 1000,
        ease: MotionTokens.easing.default
      }}
      className={className}
    >
      {children}
    </motion.section>
  );
}
