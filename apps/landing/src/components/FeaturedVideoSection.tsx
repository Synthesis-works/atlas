import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { useGlassGlare } from '@/lib/useGlassGlare';

export default function FeaturedVideoSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView   = useInView(sectionRef, { once: false, margin: '-100px' });
  const panelGlare = useGlassGlare<HTMLDivElement>();
  const btnGlare   = useGlassGlare<HTMLButtonElement>();

  return (
    <section className="py-12 md:py-20 px-6">
      <motion.div
        ref={sectionRef}
        initial={{ opacity: 0, y: 60 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 60 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        /*
          Outer wrapper is relative + rounded but NOT overflow:hidden —
          the glass ::after glare on child panels must not be clipped.
          The video gets its own overflow:hidden clip container.
        */
        className="liquid-glass-card max-w-6xl mx-auto rounded-3xl relative"
      >
        {/* Video clip container — overflow:hidden only on this inner div */}
        <div className="relative overflow-hidden rounded-3xl aspect-video">
          <video
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260402_054547_9875cfc5-155a-4229-8ec8-b7ba7125cbf8.mp4"
            className="w-full h-full object-cover"
            muted autoPlay loop playsInline preload="auto"
          />
          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/15 to-transparent pointer-events-none" />
        </div>

        {/* Bottom overlay — positioned absolutely over the video, outside the clip */}
        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-10 flex flex-col md:flex-row md:justify-between md:items-end gap-5 pointer-events-none">
          {/* Text panel — liquid-glass with glare, pointer-events restored */}
          <div
            ref={panelGlare}
            className="liquid-glass rounded-2xl p-5 md:p-7 max-w-sm pointer-events-auto"
          >
            <p className="text-white/40 text-xs tracking-[0.18em] uppercase mb-3">Our Approach</p>
            <p className="text-white text-sm md:text-base leading-relaxed">
              Atlas connects every benchmark, model, and dataset into a single evaluation
              workspace — one operating system for the entire AI evaluation lifecycle.
            </p>
          </div>

          {/* Explore button — liquid-glass with glare */}
          <motion.button
            ref={btnGlare}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            className="liquid-glass self-start md:self-auto rounded-full px-7 py-2.5 text-white/80 hover:text-white text-sm font-medium transition-colors duration-200 cursor-pointer pointer-events-auto"
          >
            Explore more
          </motion.button>
        </div>
      </motion.div>
    </section>
  );
}
