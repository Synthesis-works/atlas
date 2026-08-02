/**
 * Atlas Design Language — Motion
 * Shared Framer Motion variants and the signature easing curve.
 * Every page composes from these so transitions feel continuous.
 */

import type { Variants, Transition } from 'framer-motion';

/** The Atlas ease-out — confident, smooth, never bouncy. */
export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
export const EASE_IN_OUT = [0.65, 0, 0.35, 1] as const;

export const baseTransition: Transition = { duration: 0.7, ease: EASE_OUT };

/** Fade + rise. The default reveal primitive. */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: baseTransition },
};

/** Fade + gentle rise. For dense lists where 24px feels heavy. */
export const fadeUpSoft: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT } },
};

/** Pure fade. For overlays, dividers, captions. */
export const fade: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.6, ease: EASE_OUT } },
};

/** Stagger container — children reveal in sequence. */
export const stagger = (staggerChildren = 0.12, delayChildren = 0.1): Variants => ({
  hidden: {},
  visible: {
    transition: { staggerChildren, delayChildren },
  },
});

/**
 * Page crossfade — used by AnimatePresence in the layouts so navigation
 * feels like moving through one continuous experience, not loading pages.
 */
export const pageCrossfade: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: EASE_OUT } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.25, ease: EASE_IN_OUT } },
};
