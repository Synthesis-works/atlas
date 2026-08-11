/**
 * Public Layout — marketing site wrapper
 *
 * Persistent Intelligence Fabric (cinematic mode) + Navbar + page crossfade + Footer.
 * Every marketing route renders inside this layout.
 */

import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { EnterAtlasTransition } from '@/components/network/EnterAtlasTransition';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { useExperience } from '@/core/ExperienceController';
import { useEffect } from 'react';

export function PublicLayout() {
  const location = useLocation();
  const { setPageTransitionKey } = useExperience();

  useEffect(() => {
    setPageTransitionKey(location.pathname);
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, [location.pathname, setPageTransitionKey]);

  return (
    <div
      className="relative min-h-screen text-white bg-black"
    >
      {/* Background watermark texture covering the entire page (including footer) on documentation route */}
      {location.pathname === '/documentation' && (
        <div className="absolute inset-0 pointer-events-none z-0">
          <div 
            className="absolute inset-0 bg-cover bg-top bg-no-repeat opacity-[0.24]"
            style={{ backgroundImage: `url('/documentation-bg.jpg')` }}
          />
        </div>
      )}

      {/* Background watermark texture covering the entire page (including footer) on research route */}
      {location.pathname === '/research' && (
        <div className="absolute inset-0 pointer-events-none z-0">
          <div 
            className="absolute inset-0 bg-cover bg-top bg-no-repeat opacity-[0.24]"
            style={{ backgroundImage: `url('/research-bg.jpg')` }}
          />
        </div>
      )}


      {/* Transition overlay (only visible during Enter Atlas) */}
      <EnterAtlasTransition />

      {/* Navigation */}
      <Navbar />

      {/* Page content — crossfade on route change */}
      <div className="relative" style={{ zIndex: 1 }}>
        <AnimatePresence mode="wait">
          <Outlet key={location.pathname} />
        </AnimatePresence>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
}
