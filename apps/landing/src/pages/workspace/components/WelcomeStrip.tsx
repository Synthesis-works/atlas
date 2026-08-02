/**
 * WelcomeStrip — time-aware greeting for the Workspace overview
 */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { stagger, fadeUp } from '@/lib/motion';
import { ACTIVE_EVALUATIONS } from '@/domain/evaluations/mock';
import { ScrambleHeading } from '@/components/motion';

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return 'GOOD MORNING';
  if (hour >= 12 && hour < 17) return 'GOOD AFTERNOON';
  if (hour >= 17 && hour < 22) return 'GOOD EVENING';
  return 'GOOD NIGHT';
}

export function WelcomeStrip() {
  const activeCount = ACTIVE_EVALUATIONS.filter(
    (e) => e.status === 'Running' || e.status === 'Scoring' || e.status === 'Loading' || e.status === 'Preparing',
  ).length;

  const [greeting, setGreeting] = useState(getGreeting);

  useEffect(() => {
    const interval = setInterval(() => {
      const newGreeting = getGreeting();
      if (newGreeting !== greeting) {
        setGreeting(newGreeting);
      }
    }, 60000);
    return () => clearInterval(interval);
  }, [greeting]);

  return (
    <motion.div
      variants={stagger(0.1, 0)}
      initial="hidden"
      animate="visible"
      className="mb-0"
    >
      <motion.div variants={fadeUp}>
        <ScrambleHeading text={greeting} delay={0} />
      </motion.div>
      <motion.p variants={fadeUp} className="mt-1 text-sm text-white/30">
        Your evaluation environment is live.
        {activeCount > 0 && (
          <span className="ml-2 text-white/50">
            {activeCount} run{activeCount > 1 ? 's' : ''} in progress.
          </span>
        )}
      </motion.p>
    </motion.div>
  );
}
