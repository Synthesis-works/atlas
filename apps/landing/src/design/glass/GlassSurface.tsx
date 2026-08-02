import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';
import { useGlassGlare } from './useGlassGlare';
import type { GlassVariant } from './types';

export interface GlassSurfaceProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: GlassVariant;
  hover?: boolean;
  children?: React.ReactNode;
}

export const GlassSurface = forwardRef<HTMLDivElement, GlassSurfaceProps>(
  ({ variant = 'glass', hover = false, className, children, ...props }, ref) => {
    const glareRef = useGlassGlare<HTMLDivElement>();

    const setRefs = (node: HTMLDivElement | null) => {
      if (typeof ref === 'function') {
        ref(node);
      } else if (ref) {
        ref.current = node;
      }
      glareRef.current = node;
    };

    if (variant === 'default') {
      return (
        <div
          ref={setRefs}
          className={cn(
            'border border-white/[0.08] bg-neutral-950/40 rounded-2xl p-6 transition-all duration-300',
            hover && 'hover:scale-[1.01] hover:-translate-y-[2px] hover:border-white/20 hover:shadow-lg',
            className
          )}
          {...props}
        >
          {children}
        </div>
      );
    }

    const isLiquid = variant === 'liquid';

    return (
      <div
        ref={setRefs}
        className={cn(
          isLiquid ? 'liquid-glass' : 'liquid-glass-card',
          'group relative transition-all duration-300',
          hover && 'hover:scale-[1.01] hover:-translate-y-[2px]',
          className
        )}
        style={{
          backdropFilter: isLiquid ? 'blur(28px) saturate(180%)' : 'blur(18px) saturate(140%)',
          WebkitBackdropFilter: isLiquid ? 'blur(28px) saturate(180%)' : 'blur(18px) saturate(140%)',
          ...props.style,
        }}
        {...props}
      >
        {/* Cursor Specular Glare Layer — evaluated directly by CSS engine via --gx/--gy */}
        <div
          className="absolute inset-0 pointer-events-none z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-[inherit]"
          style={{
            background: `radial-gradient(160px circle at var(--gx, 25%) var(--gy, 15%), rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.02) 45%, transparent 70%)`,
          }}
        />
        {/* Inner children content */}
        <div className="relative z-0 h-full w-full rounded-[inherit]">{children}</div>
      </div>
    );
  }
);

GlassSurface.displayName = 'GlassSurface';
