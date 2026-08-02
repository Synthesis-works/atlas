/**
 * InteractiveGlass — Reusable interaction wrapper
 *
 * Adds mouse-tilt parallax (subtle 3D rotation + translation) and a dynamic
 * hover spotlight sheen that follows the user's cursor.
 * Respects prefers-reduced-motion.
 */

import { type ReactNode, useRef, useState, useEffect } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';

interface InteractiveGlassProps {
  children: ReactNode;
  className?: string;
  maxTilt?: number; // max tilt angle in degrees
  maxShift?: number; // max translation shift in pixels
}

export function InteractiveGlass({
  children,
  className,
  maxTilt = 6,
  maxShift = 8,
}: InteractiveGlassProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  // Spot light position coordinates relative to element bounding box
  const [spotlightPos, setSpotlightPos] = useState({ x: -9999, y: -9999 });

  // Motion values for tilt and translate
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Springs for smooth movement
  const springConfig = { damping: 26, stiffness: 140 };
  const rotateX = useSpring(useTransform(mouseY, [-0.5, 0.5], [maxTilt, -maxTilt]), springConfig);
  const rotateY = useSpring(useTransform(mouseX, [-0.5, 0.5], [-maxTilt, maxTilt]), springConfig);
  const translateX = useSpring(useTransform(mouseX, [-0.5, 0.5], [-maxShift, maxShift]), springConfig);
  const translateY = useSpring(useTransform(mouseY, [-0.5, 0.5], [-maxShift, maxShift]), springConfig);

  // Detect prefers-reduced-motion
  useEffect(() => {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    
    // Calculate normalized coordinates (-0.5 to 0.5) relative to element center
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;

    mouseX.set(x);
    mouseY.set(y);

    // Spotlight cursor position relative to the element (px)
    setSpotlightPos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
    setSpotlightPos({ x: -9999, y: -9999 });
  };

  // Render wrapper
  return (
    <motion.div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={className}
      style={
        prefersReducedMotion
          ? {}
          : {
              rotateX,
              rotateY,
              x: translateX,
              y: translateY,
              transformStyle: 'preserve-3d',
            }
      }
    >
      <div className="relative h-full w-full overflow-hidden rounded-[inherit]">
        {/* Dynamic Spotlight Glow reflection following the cursor */}
        {!prefersReducedMotion && (
          <div
            className="absolute inset-0 pointer-events-none z-10 transition-opacity duration-300"
            style={{
              background: `radial-gradient(150px circle at ${spotlightPos.x}px ${spotlightPos.y}px, rgba(255, 255, 255, 0.07), transparent 80%)`,
            }}
          />
        )}
        
        {children}
      </div>
    </motion.div>
  );
}
