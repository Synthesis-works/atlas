/**
 * Atlas PageHero — ADL primitive
 *
 * The hero section that opens every major page. Immediately communicates
 * purpose before introducing content. Composed from ADL Typography primitives.
 */

import { type ReactNode } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { fadeUp, stagger } from '@/lib/motion';
import { Display } from '@/design/Typography';
import { Eyebrow } from '@/design/primitives';

interface PageHeroProps {
  eyebrow: string;
  title: string;
  accent?: string;
  description?: string;
  cta?: ReactNode;
  className?: string;
}

export function PageHero({
  eyebrow,
  title,
  accent,
  description,
  cta,
  className,
}: PageHeroProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: false, margin: '-80px' });

  return (
    <section
      ref={ref}
      className={`relative min-h-[clamp(420px,52vh,580px)] flex flex-col items-center justify-center px-6 py-16 md:py-20 ${className ?? ''}`}
    >
      <motion.div
        className="flex flex-col items-center text-center max-w-3xl"
        variants={stagger(0.1, 0.1)}
        initial="hidden"
        animate={isInView ? 'visible' : 'hidden'}
      >
        <motion.div variants={fadeUp}>
          <Eyebrow>{eyebrow}</Eyebrow>
        </motion.div>

        <motion.div variants={fadeUp} className="mt-4">
          <Display accent={accent}>{title}</Display>
        </motion.div>

        {description && (
          <motion.p
            variants={fadeUp}
            className="mt-6 text-lg text-white/40 max-w-lg leading-relaxed"
          >
            {description}
          </motion.p>
        )}

        {cta && <motion.div variants={fadeUp} className="mt-8">{cta}</motion.div>}
      </motion.div>
    </section>
  );
}
