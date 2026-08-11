/**
 * Landing Page — the cinematic marketing experience
 *
 * Exclusive home of the video hero. The landing page introduces Atlas,
 * communicates the vision, and guides users toward Enter Atlas or Sign Up.
 * No inline navbar here — the shared Navbar from PublicLayout handles that.
 */

import { motion } from 'framer-motion';
import { pageCrossfade } from '@/lib/motion';
import HeroSection from '@/components/HeroSection';
import AboutSection from '@/components/AboutSection';
import FeaturedVideoSection from '@/components/FeaturedVideoSection';
import PhilosophySection from '@/components/PhilosophySection';
import ScientificByDesignSection from '@/components/ScientificByDesignSection';
import ServicesSection from '@/components/ServicesSection';

export default function Landing() {
  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit" className="relative">
      <HeroSection />
      <AboutSection />
      <FeaturedVideoSection />
      <PhilosophySection />
      <ScientificByDesignSection />
      <ServicesSection />
    </motion.div>
  );
}
