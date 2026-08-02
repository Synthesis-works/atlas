/**
 * Enter Atlas Transition — the boundary crossing
 *
 * When the user clicks "Enter Atlas", this component orchestrates the visual
 * transition from marketing to Workspace. It reads transitionPhase from the
 * ExperienceController and renders:
 *
 *   1. Dissolve — marketing UI fades out (blur + scale down)
 *   2. Reorganize — Fabric intensifies at center
 *   3. Materialize — Workspace chrome fades in
 *   4. Settle — transition completes
 *
 * v1 is simple and robust; polish (richer dissolve, Fabric reorganisation
 * keyframes) is deferred to Phase 6.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { useExperience } from '@/core/ExperienceController';

export function EnterAtlasTransition() {
  const { transitionPhase } = useExperience();
  const isActive = transitionPhase !== 'idle';

  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 pointer-events-none"
          style={{ zIndex: 100 }}
        >
          {/* Dissolve overlay — blurs the marketing UI behind it */}
          <motion.div
            initial={{ backdropFilter: 'blur(0px)', opacity: 0 }}
            animate={
              transitionPhase === 'dissolve'
                ? { backdropFilter: 'blur(12px)', opacity: 1 }
                : transitionPhase === 'reorganize'
                  ? { backdropFilter: 'blur(24px)', opacity: 0.8 }
                  : { backdropFilter: 'blur(0px)', opacity: 0 }
            }
            transition={{ duration: 0.6 }}
            className="absolute inset-0"
            style={{ background: 'color-mix(in srgb, var(--color-ink-2) 60%, transparent)' }}
          />

          {/* Center bloom — the Fabric "opens" at the center */}
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={
              transitionPhase === 'reorganize'
                ? { scale: 1, opacity: 1 }
                : transitionPhase === 'materialize'
                  ? { scale: 3, opacity: 0.6 }
                  : { scale: 4, opacity: 0 }
            }
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                       w-[600px] h-[600px] rounded-full ambient-bloom"
            style={{
              background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 40%, transparent 70%)',
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
