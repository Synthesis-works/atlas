/**
 * Atlas Footer — ADL primitive
 *
 * Liquid-glass footer with Atlas logomark, values strip, and copyright.
 * Used on all marketing pages.
 */

import { motion } from 'framer-motion';
import { NavLink } from 'react-router-dom';

const VALUES = ['Open Source', 'Research Driven', 'Local First', 'Built for Labs'];

const FOOTER_LINKS = [
  { label: 'Documentation', to: '/documentation' },
  { label: 'GitHub', href: 'https://github.com/Synthesis-works/atlas', external: true },
  { label: 'Research', to: '/research' },
  { label: 'Contact', href: '#' },
] as const;

export function Footer() {
  return (
    <motion.footer
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: false }}
      transition={{ duration: 0.6 }}
      className="relative py-24 px-6"
    >
      {/* Subtle top divider */}
      <div className="max-w-5xl mx-auto border-t border-white/[0.05] pt-16">
        {/* Atlas wordmark */}
        <div className="flex items-center justify-center gap-2 mb-10">
          <svg width="18" height="18" viewBox="0 0 28 28" fill="none" className="text-white/20 shrink-0" aria-hidden="true">
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
          <span className="text-sm font-semibold text-white/20 tracking-tight">Atlas</span>
        </div>

        {/* Values strip */}
        <div className="flex flex-wrap items-center justify-center gap-2 mb-10">
          {VALUES.map((value) => (
            <span
              key={value}
              className="text-xs px-3 py-1 rounded-full bg-white/[0.02] border border-white/[0.05] text-white/25"
            >
              {value}
            </span>
          ))}
        </div>

        {/* Links */}
        <nav aria-label="Footer navigation" className="flex flex-wrap items-center justify-center gap-6 mb-10">
          {FOOTER_LINKS.map((link) => {
            if ('to' in link) {
              return (
                <NavLink
                  key={link.label}
                  to={link.to}
                  className="text-sm text-white/20 hover:text-white/50 transition-colors duration-200"
                >
                  {link.label}
                </NavLink>
              );
            }
            return (
              <a
                key={link.label}
                href={link.href}
                {...(('external' in link && link.external) ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                className="text-sm text-white/20 hover:text-white/50 transition-colors duration-200"
              >
                {link.label}
              </a>
            );
          })}
        </nav>

        {/* Copyright */}
        <p className="text-xs text-white/10 text-center">
          &copy; {new Date().getFullYear()} Synthesis Works. All rights reserved.
        </p>
      </div>
    </motion.footer>
  );
}
