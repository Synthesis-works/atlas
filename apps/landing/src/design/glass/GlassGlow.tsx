import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface GlassGlowProps {
  active?: boolean;
  className?: string;
  duration?: number;
}

export function GlassGlow({ active = false, className, duration = 1200 }: GlassGlowProps) {
  const [shouldAnimate, setShouldAnimate] = useState(false);

  useEffect(() => {
    if (active) {
      setShouldAnimate(true);
      const timer = setTimeout(() => {
        setShouldAnimate(false);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [active, duration]);

  if (!shouldAnimate) return null;

  return (
    <>
      <style>{`
        @keyframes light-sweep-once {
          0% { transform: translateX(-150%) skewX(-20deg); }
          100% { transform: translateX(250%) skewX(-20deg); }
        }
        @keyframes border-flash-once {
          0% { opacity: 0; }
          20% { opacity: 1; }
          100% { opacity: 0; }
        }
      `}</style>
      <div
        className={cn(
          'absolute inset-0 pointer-events-none overflow-hidden rounded-[inherit] z-20',
          className
        )}
      >
        {/* Shimmer sweep */}
        <div
          className="absolute top-0 bottom-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent skew-x-[-20deg]"
          style={{
            animation: `light-sweep-once ${duration}ms cubic-bezier(0.16, 1, 0.3, 1) forwards`,
          }}
        />
        {/* Soft edge bezel flash */}
        <div
          className="absolute inset-0 border border-indigo-400/40 rounded-[inherit] opacity-0"
          style={{
            animation: `border-flash-once ${duration}ms ease-out forwards`,
          }}
        />
      </div>
    </>
  );
}
