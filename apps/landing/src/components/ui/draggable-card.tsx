/**
 * DraggableCard — Atlas draggable glass card primitive
 *
 * Bugs fixed:
 * 1. animate() was called on plain numbers (info.point.x/y) — framer-motion's
 *    animate() needs a MotionValue. Now animates the x/y MotionValues directly.
 * 2. transform-3d Tailwind class doesn't exist — replaced with style prop.
 * 3. dragConstraints window-center math was wrong — now uses proper viewport bounds.
 * 4. whileHover scale conflicted with active drag state — disabled during drag.
 * 5. z-index not managed — dragging card now lifts to z-50 via state.
 * 6. body cursor leak on unmount — cleanup runs in useEffect return.
 * 7. Glare div used bg-white (100% white flash) — now a soft radial gradient.
 * 8. DraggableCardContainer was missing position:relative for absolute children.
 */

import { cn } from '@/lib/utils';
import React, {
  useRef, useState, useEffect, useCallback,
  type ReactNode, type RefObject,
} from 'react';
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useVelocity,
  useAnimationControls,
  animate,
} from 'framer-motion';

/* ── spring config ─────────────────────────────────────────────────────── */
const SPRING = { stiffness: 120, damping: 22, mass: 0.5 } as const;

/* ── DraggableCardBody ──────────────────────────────────────────────────── */
export const DraggableCardBody = ({
  className,
  children,
  style,
  dragBoundsRef,
}: {
  className?: string;
  children?: ReactNode;
  style?: React.CSSProperties;
  dragBoundsRef?: RefObject<HTMLElement | null>;
}) => {
  const cardRef   = useRef<HTMLDivElement>(null);
  const controls  = useAnimationControls();
  const [isDragging, setIsDragging] = useState(false);

  /* Mouse-relative offset from card centre — drives tilt */
  const mouseX  = useMotionValue(0);
  const mouseY  = useMotionValue(0);

  /* Positional MotionValues for the card (drag uses these) */
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const velocityX = useVelocity(x);
  const velocityY = useVelocity(y);

  /* Tilt */
  const rotateX = useSpring(useTransform(mouseY, [-300, 300], [15, -15]), SPRING);
  const rotateY = useSpring(useTransform(mouseX, [-300, 300], [-15, 15]), SPRING);

  /* Soft glare opacity — fades in from edges */
  const glareOpacity = useSpring(
    useTransform(mouseX, [-300, 0, 300], [0.12, 0, 0.12]),
    SPRING,
  );

  /* Keep a draggable inside its local tool area when one is provided. */
  const [constraints, setConstraints] = useState({ top: 0, left: 0, right: 0, bottom: 0 });

  const updateConstraints = useCallback(() => {
    const el  = cardRef.current;
    const bounds = dragBoundsRef?.current?.getBoundingClientRect();
    const card = el?.getBoundingClientRect();
    const pad = 16;

    if (bounds && card) {
      setConstraints({
        top: bounds.top - card.top + pad,
        left: bounds.left - card.left + pad,
        right: bounds.right - card.right - pad,
        bottom: bounds.bottom - card.bottom - pad,
      });
      return;
    }

    const w   = el?.offsetWidth  ?? 320;
    const h   = el?.offsetHeight ?? 380;
    setConstraints({
      top:    -(window.innerHeight / 2 - h / 2 - pad),
      left:   -(window.innerWidth  / 2 - w / 2 - pad),
      right:   window.innerWidth  / 2 - w / 2 - pad,
      bottom:  window.innerHeight / 2 - h / 2 - pad,
    });
  }, [dragBoundsRef]);

  useEffect(() => {
    updateConstraints();
    window.addEventListener('resize', updateConstraints);
    return () => {
      window.removeEventListener('resize', updateConstraints);
      /* Safety: restore cursor if drag was interrupted */
      document.body.style.cursor = '';
    };
  }, [updateConstraints]);

  /* ── handlers ────────────────────────────────────────────────────────── */
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isDragging) return; // no tilt while dragging
    const rect = cardRef.current?.getBoundingClientRect();
    if (!rect) return;
    const dx = e.clientX - (rect.left + rect.width  / 2);
    const dy = e.clientY - (rect.top  + rect.height / 2);
    mouseX.set(dx);
    mouseY.set(dy);
    // CSS vars for the glare radial position (0–100%)
    const gx = ((e.clientX - rect.left) / rect.width  * 100).toFixed(1);
    const gy = ((e.clientY - rect.top)  / rect.height * 100).toFixed(1);
    cardRef.current?.style.setProperty('--gx', `${gx}%`);
    cardRef.current?.style.setProperty('--gy', `${gy}%`);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  const handleDragStart = () => {
    setIsDragging(true);
    document.body.style.cursor = 'grabbing';
  };

  const handleDragEnd = () => {
    setIsDragging(false);
    document.body.style.cursor = '';

    /* Reset tilt */
    controls.start({
      rotateX: 0,
      rotateY: 0,
      transition: { type: 'spring', ...SPRING },
    });

    /* Inertial settle — animate the MotionValues, not raw numbers */
    const vx  = velocityX.get();
    const vy  = velocityY.get();
    const maxX = constraints.right;
    const minX = constraints.left;
    const maxY = constraints.bottom;
    const minY = constraints.top;

    const targetX = Math.min(Math.max(x.get() + vx * 0.12, minX), maxX);
    const targetY = Math.min(Math.max(y.get() + vy * 0.12, minY), maxY);

    animate(x, targetX, { type: 'spring', stiffness: 60, damping: 18, mass: 0.9 });
    animate(y, targetY, { type: 'spring', stiffness: 60, damping: 18, mass: 0.9 });
  };

  return (
    <motion.div
      ref={cardRef}
      drag
      dragConstraints={constraints}
      dragElastic={0.08}
      dragMomentum={false} /* we handle inertia manually above */
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      animate={controls}
      style={{
        x,
        y,
        rotateX,
        rotateY,
        willChange: 'transform',
        transformStyle: 'preserve-3d',
        zIndex: isDragging ? 50 : 20,
        ...style,
      }}
      /* Only scale on hover when NOT dragging */
      whileHover={isDragging ? {} : { scale: 1.015 }}
      whileTap={{ scale: 0.99 }}
      className={cn(
        'relative touch-none select-none cursor-grab active:cursor-grabbing',
        'rounded-3xl overflow-hidden',
        className,
      )}
    >
      {children}

      {/* Cursor-tracked specular glare — soft radial, not solid white */}
      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 select-none rounded-[inherit]"
        style={{ opacity: glareOpacity }}
      >
        <div
          className="absolute inset-0 rounded-[inherit]"
          style={{
            background: 'radial-gradient(circle at var(--gx, 50%) var(--gy, 50%), rgba(255,255,255,0.28) 0%, transparent 60%)',
          }}
        />
      </motion.div>
    </motion.div>
  );
};

/* ── DraggableCardContainer ─────────────────────────────────────────────── */
export const DraggableCardContainer = ({
  className,
  children,
}: {
  className?: string;
  children?: ReactNode;
}) => (
  /*
    position:relative is required so absolutely-positioned card children
    sit within this stacking context, not relative to the viewport.
    perspective:3000px enables the 3D tilt effect.
  */
  <div
    className={cn('relative [perspective:3000px]', className)}
    style={{ isolation: 'isolate' }}
  >
    {children}
  </div>
);
