import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ArrowUpRight } from 'lucide-react';

const MODULES = [
  {
    tag: 'Execution',
    title: 'Sandbox Benchmarking',
    description:
      'Deploy and execute complex benchmarks safely in secure sandboxes. Run standardised reasoning, mathematics, coding, and safety evaluations with ease.',
    src: 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260314_131748_f2ca2a28-fed7-44c8-b9a9-bd9acdd5ec31.mp4',
  },
  {
    tag: 'Analytics',
    title: 'Unified Leaderboard',
    description:
      'Aggregated evaluation reports, granular capability profiles, and comparison metrics compiled into interactive visualisation tools.',
    src: 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260324_151826_c7218672-6e92-402c-9e45-f1e0f454bdc4.mp4',
  },
];

export default function ServicesSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, margin: '-100px' });

  return (
    <section className="relative py-24 md:py-32 px-6 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(255,255,255,0.02)_0%,_transparent_60%)] pointer-events-none" />

      <div className="relative z-10 max-w-6xl mx-auto" ref={ref}>
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.7 }}
          className="flex justify-between items-end mb-14"
        >
          <h2 className="text-3xl md:text-5xl text-white tracking-tight">Core Modules</h2>
          <span className="text-white/30 text-sm hidden md:block">System Capabilities</span>
        </motion.div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
          {MODULES.map((mod, i) => (
            <motion.div
              key={mod.tag}
              initial={{ opacity: 0, y: 50 }}
              animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 50 }}
              transition={{ duration: 0.8, delay: i * 0.15 }}
              className="liquid-glass-card rounded-3xl group"
            >
              {/* Video area */}
              <div className="relative overflow-hidden rounded-t-3xl aspect-video">
                <video
                  src={mod.src}
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-[1.03]"
                  muted
                  autoPlay
                  loop
                  playsInline
                  preload="auto"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent pointer-events-none" />
              </div>

              {/* Copy */}
              <div className="p-6 md:p-8">
                <div className="flex justify-between items-start mb-4">
                  <span className="uppercase tracking-[0.15em] text-white/30 text-xs">
                    {mod.tag}
                  </span>
                  <div className="liquid-glass rounded-full p-2 opacity-60 group-hover:opacity-100 transition-opacity duration-300">
                    <ArrowUpRight className="w-4 h-4 text-white" />
                  </div>
                </div>
                <h3 className="text-white text-xl md:text-2xl mb-3 tracking-tight font-semibold">
                  {mod.title}
                </h3>
                <p className="text-white/45 text-sm leading-relaxed">{mod.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
