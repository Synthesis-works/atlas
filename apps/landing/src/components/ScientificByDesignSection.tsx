import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ShieldCheck, History, FileCheck } from 'lucide-react';

const PRINCIPLES = [
  {
    icon: ShieldCheck,
    title: 'Evidence Before Interpretation',
    tagline: 'Every conclusion begins with measurable evidence.',
    caption: 'Metrics are recorded before any analysis is generated.',
  },
  {
    icon: History,
    title: 'Immutable Versioning',
    tagline: 'Every execution context is permanently reproducible.',
    caption: 'Benchmarks, templates, and libraries are versioned.',
  },
  {
    icon: FileCheck,
    title: 'Standardized Verification',
    tagline: 'Every evaluation follows the same verification protocol.',
    caption: 'Validating schema, licenses, and data before publish.',
  },
];

export default function ScientificByDesignSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, margin: '-100px' });

  return (
    <section ref={ref} className="relative py-24 md:py-32 px-6 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,_rgba(99,102,241,0.03)_0%,_transparent_60%)] pointer-events-none" />
      
      <div className="relative z-10 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.7 }}
          className="text-center mb-16 md:mb-24"
        >
          <p className="text-white/30 text-xs tracking-[0.2em] uppercase mb-4">Integrity Standards</p>
          <h2 className="text-3xl md:text-5xl text-white tracking-tight">Scientific by Design</h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PRINCIPLES.map((p, i) => {
            const Icon = p.icon;
            return (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 40 }}
                animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 40 }}
                transition={{ duration: 0.8, delay: i * 0.12 }}
                className="liquid-glass-card rounded-2xl p-6 md:p-8 flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="liquid-glass rounded-lg p-2.5 w-fit">
                    <Icon className="w-5 h-5 text-accent" />
                  </div>
                  <h3 className="text-white text-base font-semibold tracking-tight">{p.title}</h3>
                  <p className="text-white/80 text-sm leading-relaxed font-serif italic">{p.tagline}</p>
                </div>
                <div className="mt-6 pt-4 border-t border-white/[0.04]">
                  <p className="text-white/30 text-xs leading-normal">{p.caption}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
