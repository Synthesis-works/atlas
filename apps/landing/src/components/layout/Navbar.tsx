/**
 * Atlas Navbar — Floating Pill (marketing site only)
 *
 * A top-positioned floating pill built on the Atlas liquid-glass surface.
 * Logo + text nav links + Sign Up / Enter Atlas CTAs. On mobile, collapses
 * to a full-screen overlay menu.
 *
 * The Workspace site has its own layout (WorkspaceLayout) and is unaffected.
 */

import { NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, ArrowRight } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useExperience } from '@/core/ExperienceController';
import { useGlassGlare } from '@/lib/useGlassGlare';

const NAV_LINKS = [
  { label: 'Platform',      to: '/platform' },
  { label: 'Benchmarks',    to: '/benchmarks' },
  { label: 'Research',      to: '/research' },
  { label: 'Documentation', to: '/documentation' },
  { label: 'Open Source',   to: '/open-source' },
  { label: 'Sandbox',       to: '/sandbox' },
] as const;

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `whitespace-nowrap px-3 py-1.5 text-sm rounded-full transition-all duration-200 ${
    isActive
      ? 'text-white bg-white/[0.08]'
      : 'text-white/40 hover:text-white/80 hover:bg-white/[0.05]'
  }`;

export function Navbar() {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { startLoader, transitionPhase } = useExperience();
  const isTransitioning = transitionPhase !== 'idle';
  const glareRef = useGlassGlare<HTMLDivElement>();

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, []);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  const AUTH_LOADER_STATES = [
    { text: 'Establishing secure handshake...' },
    { text: 'Loading authentication modules...' },
    { text: 'Connecting to identity provider...' },
    { text: 'Redirecting to entry portal...' },
  ];

  const handleEnter = () => {
    setMobileOpen(false);
    startLoader(AUTH_LOADER_STATES, 400, () => navigate('/login'));
  };

  return (
    <>
      <motion.nav
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: isTransitioning ? 0 : 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="fixed top-0 inset-x-0 z-40 px-4 pt-4 pointer-events-none"
        aria-label="Main navigation"
      >
        <div className="mx-auto max-w-6xl pointer-events-auto">
          {/*
            The pill uses liquid-glass (overflow: visible is the default)
            so the ::before gradient border renders correctly.
          */}
          <div ref={glareRef} className="liquid-glass rounded-full px-3 py-2 flex items-center justify-between gap-2">

            {/* Logo */}
            <NavLink
              to="/"
              className="flex items-center gap-2 px-2 py-1 rounded-full hover:bg-white/[0.05] transition-colors duration-200 shrink-0"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 28 28"
                fill="none"
                className="text-white/70 shrink-0"
                aria-hidden="true"
              >
                <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="14" cy="11" r="2.5" fill="currentColor" opacity="0.15" />
                  <circle cx="14" cy="11" r="2.5" />
                  <line x1="14" y1="8.5" x2="7" y2="24" />
                  <line x1="14" y1="8.5" x2="21" y2="24" />
                  <line x1="9.5" y1="18" x2="18.5" y2="18" />
                  <line x1="14" y1="8.5" x2="14" y2="3" />
                  <line x1="14" y1="11" x2="6" y2="7" />
                  <line x1="14" y1="11" x2="22" y2="7" />
                  <circle cx="14" cy="3" r="1.25" />
                  <circle cx="6" cy="7" r="1.25" />
                  <circle cx="22" cy="7" r="1.25" />
                </g>
              </svg>
              <span className="text-sm font-semibold text-white/70">Atlas</span>
            </NavLink>

            {/* Desktop links — hidden below lg */}
            <div className="hidden lg:flex items-center gap-0.5 flex-1 justify-center">
              {NAV_LINKS.map((link) => (
                <NavLink key={link.to} to={link.to} className={linkClass}>
                  {link.label}
                </NavLink>
              ))}
            </div>

            {/* CTA row */}
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={handleEnter}
                className="hidden lg:block whitespace-nowrap px-3 py-1.5 text-sm text-white/30 hover:text-white/60 rounded-full hover:bg-white/[0.04] transition-all duration-200 cursor-pointer"
              >
                Sign Up
              </button>

              <motion.button
                whileTap={{ scale: 0.96 }}
                onClick={handleEnter}
                disabled={isTransitioning}
                className="hidden lg:inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium rounded-full
                           text-white transition-colors duration-200 disabled:opacity-40 cursor-pointer
                           whitespace-nowrap"
                style={{ background: 'var(--color-accent)' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-accent-hover)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--color-accent)')}
              >
                Enter Atlas
                <ArrowRight className="w-3.5 h-3.5 shrink-0" />
              </motion.button>

              {/* Mobile hamburger */}
              <button
                className="lg:hidden p-2 rounded-full hover:bg-white/[0.06] text-white/50 hover:text-white transition-colors cursor-pointer"
                onClick={() => setMobileOpen((v) => !v)}
                aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={mobileOpen}
              >
                {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            key="mobile-menu"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-30 flex flex-col items-center justify-center gap-5 px-6 lg:hidden"
            style={{ background: 'rgba(0,0,0,0.92)', backdropFilter: 'blur(24px)' }}
          >
            {NAV_LINKS.map((link, i) => (
              <motion.div
                key={link.to}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.3 }}
              >
                <NavLink
                  to={link.to}
                  onClick={() => setMobileOpen(false)}
                  className="text-xl text-white/60 hover:text-white transition-colors"
                >
                  {link.label}
                </NavLink>
              </motion.div>
            ))}

            <div className="w-10 h-px bg-white/[0.08] my-2" />

            <motion.button
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: NAV_LINKS.length * 0.06 }}
              onClick={handleEnter}
              className="text-base text-white/35 hover:text-white/60 transition-colors cursor-pointer"
            >
              Sign Up
            </motion.button>

            <motion.button
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: (NAV_LINKS.length + 1) * 0.06 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleEnter}
              className="liquid-glass inline-flex items-center gap-2 rounded-full px-7 py-3 text-sm font-medium text-white cursor-pointer"
            >
              Enter Atlas
              <ArrowRight className="w-4 h-4" />
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
