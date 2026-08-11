import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

export default function PhilosophySection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, margin: '-100px' });

  return (
    <section className="py-24 md:py-32 px-6 overflow-hidden">
      <div className="max-w-6xl mx-auto" ref={ref}>
        <motion.h2
          initial={{ opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 40 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="text-4xl md:text-6xl lg:text-7xl text-white tracking-tight mb-16 md:mb-20 leading-[1.05]"
        >
          Evaluation{' '}
          <span className="font-serif italic text-white/30">×</span>{' '}
          Intelligence
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-16 items-center">
          {/* Left: Video */}
          <motion.div
            initial={{ opacity: 0, x: -32 }}
            animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: -32 }}
            transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="liquid-glass-card rounded-3xl overflow-hidden aspect-[4/3]"
          >
            <video
              src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260307_083826_e938b29f-a43a-41ec-a153-3d4730578ab8.mp4"
              className="w-full h-full object-cover"
              muted
              autoPlay
              loop
              playsInline
              preload="auto"
            />
          </motion.div>

          {/* Right: Text blocks */}
          <motion.div
            initial={{ opacity: 0, x: 32 }}
            animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 32 }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col justify-center"
          >
            <div className="mb-10">
              <p className="text-white/30 text-xs tracking-[0.18em] uppercase mb-4">
                Unified Workspace
              </p>
              <p className="text-white/70 text-base md:text-lg leading-relaxed">
                Today, AI evaluation is fragmented across platforms — benchmarks scattered,
                models tested in isolation, reports lost in email threads. Atlas brings
                every dimension of evaluation into a single, connected operating system
                where insights flow naturally between components.
              </p>
            </div>

            <div className="w-full h-px bg-white/[0.08] mb-10" />

            <div>
              <p className="text-white/30 text-xs tracking-[0.18em] uppercase mb-4">
                Built for Research Labs
              </p>
              <p className="text-white/70 text-base md:text-lg leading-relaxed">
                Whether you're running MMLU against GPT-4 or comparing Claude's reasoning
                capabilities, Atlas provides the structured environment to execute
                evaluations, track results, and generate comprehensive reports — all from
                one workspace.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
