/**
 * HeroSection — the cinematic video hero (exclusive to the landing page)
 *
 * Configured to loop the local video natively to eliminate lag,
 * and features a bottom-heavy gradient overlay for optimal contrast.
 */

import { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { useExperience } from '@/core/ExperienceController';
import { useGlassGlare } from '@/lib/useGlassGlare';

export default function HeroSection() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const { transitionPhase, startLoader } = useExperience();
  const pillGlareRef  = useGlassGlare<HTMLDivElement>();
  const enterGlareRef = useGlassGlare<HTMLButtonElement>();

  const handleCanPlay = () => {
    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
      videoRef.current.style.opacity = '1';
    }
  };

  return (
    <div className="min-h-screen overflow-hidden relative flex flex-col">
      {/* Background video */}
      <video
        ref={videoRef}
        src="/video-hero.mp4"
        className="absolute inset-0 w-full h-full object-cover pointer-events-none transition-opacity duration-700 ease-in-out"
        muted
        autoPlay
        playsInline
        preload="auto"
        loop
        style={{ opacity: 0, transform: 'translateZ(0)', willChange: 'opacity' }}
        onCanPlay={handleCanPlay}
      />

      {/* Soft gradient overlay — darkened at top for navbar readability, gentle fade at bottom to keep video visible */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/55 via-black/15 to-black/30 pointer-events-none" />

      {/* Hero content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 pt-32 pb-24 text-center">
        {/* Eyebrow */}
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-white/45 text-xs tracking-[0.2em] uppercase mb-6"
        >
          Atlas by Synthesis Works
        </motion.p>

        {/* Main headline */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="text-[clamp(3rem,10vw,7.5rem)] text-white tracking-tight leading-[1.0] mb-6 max-w-3xl"
          style={{
            fontFamily: "'Instrument Serif', serif",
            textShadow: '0 2px 20px rgba(0,0,0,0.5)',
          }}
        >
          Evaluate <em style={{ fontStyle: 'italic' }}>AI</em>.
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="text-white/70 text-base md:text-lg leading-relaxed max-w-md mb-10"
          style={{ textShadow: '0 1px 8px rgba(0,0,0,0.4)' }}
        >
          The operating system for AI evaluation. Unify benchmarks, models, datasets,
          and reporting in one intelligent workspace.
        </motion.p>

        {/* Email capture pill */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-md mb-5"
        >
          <div
            ref={pillGlareRef}
            className="liquid-glass rounded-full flex items-center gap-2 pl-5 pr-2 py-2"
          >
            <label htmlFor="hero-email" className="sr-only">
              Email address for early access
            </label>
            <input
              id="hero-email"
              type="email"
              placeholder="Enter your email for early access"
              autoComplete="email"
              className="flex-1 min-w-0 bg-transparent text-white text-sm placeholder:text-white/30 outline-none"
            />
            <button
              type="button"
              aria-label="Request early access"
              className="shrink-0 bg-white text-black rounded-full p-2.5 hover:bg-white/90 active:scale-95 transition-all duration-200 cursor-pointer"
            >
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </motion.div>

        {/* Enter Atlas CTA */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <motion.button
            ref={enterGlareRef}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => {
              const AUTH_LOADER_STATES = [
                { text: "Establishing secure handshake..." },
                { text: "Loading authentication modules..." },
                { text: "Connecting to identity provider..." },
                { text: "Redirecting to entry portal..." }
              ];
              startLoader(AUTH_LOADER_STATES, 400, () => navigate('/login'));
            }}
            disabled={transitionPhase !== 'idle'}
            className="liquid-glass inline-flex items-center gap-2 rounded-full px-7 py-2.5 text-sm font-medium text-white/80 hover:text-white transition-colors duration-200 cursor-pointer disabled:opacity-40 border border-white/5 hover:border-white/15"
          >
            Enter Atlas
            <ArrowRight className="w-3.5 h-3.5" />
          </motion.button>
        </motion.div>
      </div>
    </div>
  );
}
