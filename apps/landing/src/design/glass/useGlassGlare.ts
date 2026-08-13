import { useRef, useEffect, useCallback, type RefObject } from 'react';

/**
 * useGlassGlare
 *
 * Tracks the cursor position within a glass element and writes
 * --gx / --gy CSS custom properties, driving the radial glare.
 * Optimized with requestAnimationFrame to prevent rendering lag.
 */
export function useGlassGlare<T extends HTMLElement>(): RefObject<T | null> {
  const ref = useRef<T | null>(null);
  const rafRef = useRef<number | null>(null);

  const onMove = useCallback((e: PointerEvent) => {
    if (rafRef.current !== null) return;

    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const gx = ((e.clientX - rect.left) / rect.width) * 100;
      const gy = ((e.clientY - rect.top) / rect.height) * 100;
      el.style.setProperty('--gx', `${gx.toFixed(1)}%`);
      el.style.setProperty('--gy', `${gy.toFixed(1)}%`);
    });
  }, []);

  const onLeave = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    const el = ref.current;
    if (!el) return;
    el.style.setProperty('--gx', '25%');
    el.style.setProperty('--gy', '15%');
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerleave', onLeave);
    return () => {
      el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerleave', onLeave);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [onMove, onLeave]);

  return ref;
}
