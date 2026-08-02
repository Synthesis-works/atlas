import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

export default function AboutSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, margin: '-100px' });

  return (
    <section
      ref={ref}
      className="relative py-24 md:py-32 px-6 overflow-hidden"
    >
      {/* Subtle radial highlight at the top */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(255,255,255,0.03)_0%,_transparent_70%)] pointer-events-none" />

      <div className="relative z-10 max-w-5xl mx-auto flex flex-col items-center text-center">
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-white/30 text-xs tracking-[0.2em] uppercase mb-8"
        >
          About Atlas
        </motion.p>

        <motion.h2
          initial={{ opacity: 0, y: 32 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 32 }}
          transition={{ duration: 0.9, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="text-4xl md:text-6xl lg:text-7xl text-white leading-[1.1] tracking-tight"
        >
          Unifying{' '}
          <span className="font-serif italic text-white/50">intelligence</span>
          {' '}for teams that{' '}
          <span className="font-serif italic text-white/50">
            evaluate, benchmark, and&nbsp;innovate.
          </span>
        </motion.h2>
      </div>
    </section>
  );
}
