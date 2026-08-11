/**
 * Atlas Visualization System — Motion Contract
 * Shared spring physics, transitions, and gesture behaviors.
 */

export const ChartMotion = {
  spring: {
    stiffness: 140,
    damping: 20,
    mass: 0.8,
  },
  snappySpring: {
    stiffness: 220,
    damping: 18,
    mass: 0.5,
  },
  transitions: {
    enter: {
      initial: { opacity: 0, scale: 0.98 },
      animate: { opacity: 1, scale: 1 },
      exit: { opacity: 0, scale: 0.98 },
      transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] },
    },
    hover: {
      transition: { duration: 0.15, ease: 'easeOut' },
    },
  },
} as const;
