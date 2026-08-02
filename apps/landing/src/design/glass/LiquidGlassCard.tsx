import React, { useRef, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useVelocity,
  useAnimationControls,
  animate,
} from 'framer-motion';
import { GlassSurface } from './GlassSurface';
import { GlassPhysics } from './glassPhysics';
import { GlassTokens } from './tokens';

interface LiquidGlassCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onDragStart' | 'onDragEnd' | 'onDrag' | 'onAnimationStart' | 'onDragTransitionEnd'> {
  children?: React.ReactNode;
  initialX?: number;
  initialY?: number;
  id: string;
  onPositionChange?: (x: number, y: number) => void;
  onDragStateChange?: (dragging: boolean) => void;
  isDraggable?: boolean;
}

export function LiquidGlassCard({
  children,
  initialX = 100,
  initialY = 100,
  id,
  onPositionChange,
  onDragStateChange,
  isDraggable = true,
  className,
  style,
  ...props
}: LiquidGlassCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const controls = useAnimationControls();

  // Track absolute positions using motion values
  const x = useMotionValue(initialX);
  const y = useMotionValue(initialY);

  // Track mouse offset within the card for hover tilt
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Physics velocities
  const velocityX = useVelocity(x);
  const velocityY = useVelocity(y);

  const springConfig = {
    stiffness: 100,
    damping: 20,
    mass: 0.5,
  };

  // Convert mouse movement to 3D rotation
  const rotateX = useSpring(
    useTransform(mouseY, [-300, 300], [GlassPhysics.maxRotation, -GlassPhysics.maxRotation]),
    springConfig
  );
  const rotateY = useSpring(
    useTransform(mouseX, [-300, 300], [-GlassPhysics.maxRotation, GlassPhysics.maxRotation]),
    springConfig
  );

  // Dynamic glare opacity based on mouse movements
  const glareOpacity = useSpring(
    useTransform(mouseX, [-300, 0, 300], [0.25, 0, 0.25]),
    springConfig
  );

  const [dragging, setDragging] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  // Keep motion values in sync with initial coordinates updates
  useEffect(() => {
    x.set(initialX);
    y.set(initialY);
  }, [initialX, initialY, x, y]);

  // Handle visibility API to throttle RAF loop when page is backgrounded
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'hidden') {
        controls.stop();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [controls]);

  // Sync prefers-reduced-motion
  useEffect(() => {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion) return;
    const { clientX, clientY } = e;
    if (!cardRef.current) return;
    const { width, height, left, top } = cardRef.current.getBoundingClientRect();
    const centerX = left + width / 2;
    const centerY = top + height / 2;
    mouseX.set(clientX - centerX);
    mouseY.set(clientY - centerY);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  // Keyboard navigation arrow controls
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const step = e.shiftKey ? 40 : 10;
    let handled = false;
    let nextX = x.get();
    let nextY = y.get();

    switch (e.key) {
      case 'ArrowLeft':
        nextX -= step;
        handled = true;
        break;
      case 'ArrowRight':
        nextX += step;
        handled = true;
        break;
      case 'ArrowUp':
        nextY -= step;
        handled = true;
        break;
      case 'ArrowDown':
        nextY += step;
        handled = true;
        break;
      default:
        break;
    }

    if (handled) {
      e.preventDefault();
      const pad = GlassPhysics.edgePadding;
      const w = cardRef.current?.offsetWidth || 300;
      const h = cardRef.current?.offsetHeight || 300;
      const cx = Math.min(Math.max(nextX, pad), window.innerWidth - w - pad);
      const cy = Math.min(Math.max(nextY, pad), window.innerHeight - h - pad);

      x.set(cx);
      y.set(cy);
      onPositionChange?.(cx, cy);
    }
  };

  return (
    <motion.div
      ref={cardRef}
      drag={isDraggable}
      dragMomentum={!prefersReducedMotion}
      dragElastic={0.1}
      onDragStart={() => {
        setDragging(true);
        onDragStateChange?.(true);
        document.body.style.cursor = 'grabbing';
      }}
      onDragEnd={() => {
        setDragging(false);
        onDragStateChange?.(false);
        document.body.style.cursor = 'default';

        // Persist final position coordinate state
        onPositionChange?.(x.get(), y.get());

        // Spring reset 3D rotation
        controls.start({
          rotateX: 0,
          rotateY: 0,
          transition: {
            type: 'spring',
            ...springConfig,
          },
        });

        if (prefersReducedMotion) return;

        // Apply spring inertial snap limits
        const vx = velocityX.get();
        const vy = velocityY.get();
        const velocityMagnitude = Math.hypot(vx, vy);
        const bounce = Math.min(0.8, velocityMagnitude / 1000);

        // Clamping check on drag release to keep items inside padding bounds
        const pad = GlassPhysics.edgePadding;
        const w = cardRef.current?.offsetWidth || 300;
        const h = cardRef.current?.offsetHeight || 300;
        
        let finalX = x.get() + vx * 0.25;
        let finalY = y.get() + vy * 0.25;
        
        // Grid snap calculation if near magnetic grid
        const grid = GlassPhysics.magneticGridSize;
        const roundedX = Math.round(finalX / grid) * grid;
        const roundedY = Math.round(finalY / grid) * grid;
        if (Math.abs(finalX - roundedX) < GlassPhysics.snapThreshold) finalX = roundedX;
        if (Math.abs(finalY - roundedY) < GlassPhysics.snapThreshold) finalY = roundedY;

        const clampedX = Math.min(Math.max(finalX, pad), window.innerWidth - w - pad);
        const clampedY = Math.min(Math.max(finalY, pad), window.innerHeight - h - pad);

        // Decelerate smoothly to final coordinates
        animate(x, clampedX, {
          type: 'spring',
          stiffness: 50,
          damping: 15,
          mass: 0.8,
          bounce,
        });

        animate(y, clampedY, {
          type: 'spring',
          stiffness: 50,
          damping: 15,
          mass: 0.8,
          bounce,
        });
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="region"
      aria-grabbed={dragging}
      aria-label="Floating liquid glass widget card"
      style={{
        x,
        y,
        rotateX: prefersReducedMotion ? 0 : rotateX,
        rotateY: prefersReducedMotion ? 0 : rotateY,
        boxShadow: dragging ? GlassTokens.shadow.lifted : GlassTokens.shadow.resting,
        willChange: 'transform',
        ...style,
      }}
      animate={controls}
      whileHover={prefersReducedMotion ? {} : { scale: GlassPhysics.hoverScale }}
      className={cn(
        'fixed left-0 top-0 select-none touch-none outline-none z-[200]',
        'focus-visible:ring-2 focus-visible:ring-indigo-500/50 rounded-3xl',
        dragging ? 'cursor-grabbing' : isDraggable ? 'cursor-grab' : '',
        className
      )}
      {...props}
    >
      <GlassSurface variant="liquid" className="h-full w-full rounded-3xl">
        {/* Specular glare dynamic sheet overlay */}
        {!prefersReducedMotion && (
          <motion.div
            style={{ opacity: glareOpacity }}
            className="pointer-events-none absolute inset-0 bg-white/5 select-none rounded-[inherit] z-10"
          />
        )}
        {children}
      </GlassSurface>
    </motion.div>
  );
}
