/**
 * useGlassGlare
 *
 * Tracks the cursor position within a liquid-glass element and writes
 * --gx / --gy CSS custom properties, driving the radial glare in the
 * ::after pseudo-element — exactly as Apple's liquid-glass.js demo does.
 *
 * Usage:
 *   const ref = useGlassGlare<HTMLDivElement>();
 *   <div ref={ref} className="liquid-glass …">…</div>
 */

import { useRef, useEffect, useCallback, type RefObject } from 'react';

export function useGlassGlare<T extends HTMLElement>(): RefObject<T | null> {
  const ref = useRef<T | null>(null);

  const onMove = useCallback((e: PointerEvent) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const gx = ((e.clientX - rect.left) / rect.width)  * 100;
    const gy = ((e.clientY - rect.top)  / rect.height) * 100;
    el.style.setProperty('--gx', `${gx.toFixed(1)}%`);
    el.style.setProperty('--gy', `${gy.toFixed(1)}%`);
  }, []);

  const onLeave = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    // Reset to default top-left on pointer leave so a static highlight remains
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
    };
  }, [onMove, onLeave]);

  return ref;
}
