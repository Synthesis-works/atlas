import React, { useRef } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { MotionTokens } from '@/design/tokens';

export interface AnimatedCardProps {
  children: React.ReactNode;
  className?: string;
  index?: number; // Used for staggered entrance
}

export function AnimatedCard({ children, className = '', index = 0 }: AnimatedCardProps) {
  const prefersReducedMotion = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);

  if (prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.95 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ 
        duration: MotionTokens.durations.base / 1000, 
        delay: (index * MotionTokens.stagger.base) / 1000,
        ease: MotionTokens.easing.default
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
