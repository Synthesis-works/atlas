/**
 * Atlas Design Language — Primitives
 * Reusable surface, card, badge, label, button, and input components.
 * Pages compose from these — never inline the styles.
 */

import { type ReactNode, type InputHTMLAttributes, type ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { GlassSurface, LiquidGlassCard, GlassGlow } from './glass';
import type { GlassVariant } from './glass/types';

export { GlassSurface, LiquidGlassCard, GlassGlow };

/* -----------------------------------------------------------------------
   Glass (Legacy adapter for compatibility)
   ----------------------------------------------------------------------- */

interface GlassProps {
  children: ReactNode;
  level?: 1 | 2 | 3;
  variant?: 'standard' | 'liquid';
  className?: string;
  as?: 'div' | 'section' | 'nav' | 'header' | 'footer';
}

const glassLevels: Record<number, string> = {
  1: 'bg-white/[0.01]',
  2: 'bg-white/[0.02]',
  3: 'bg-white/[0.04]',
};

export function Glass({
  children,
  level = 2,
  variant = 'standard',
  className,
  as: Component = 'div',
}: GlassProps) {
  const isLiquid = variant === 'liquid';

  return (
    <Component
      className={cn(
        isLiquid 
          ? 'relative bg-white/[0.05] border border-white/[0.18]' 
          : cn('liquid-glass-card', glassLevels[level]),
        className
      )}
      style={
        isLiquid
          ? {
              backdropFilter: 'blur(2px)',
              WebkitBackdropFilter: 'blur(2px)',
              boxShadow: 
                'inset 0 1px 0 rgba(255, 255, 255, 0.2), inset 0 -1px 0 rgba(255, 255, 255, 0.03), 0 0 40px rgba(79, 140, 255, 0.1), 0 30px 60px rgba(0, 0, 0, 0.4)',
            }
          : undefined
      }
    >
      {isLiquid && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden z-10 rounded-[inherit]">
          <div 
            className="absolute top-0 bottom-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/[0.08] to-transparent animate-light-sweep"
            style={{ transformOrigin: 'top left' }}
          />
        </div>
      )}
      <div className="relative z-0 h-full w-full rounded-[inherit]">{children}</div>
    </Component>
  );
}

/* -----------------------------------------------------------------------
   Card
   A high-performance Glass surface with hover lift and glare tracking.
   ----------------------------------------------------------------------- */

interface CardProps {
  children: ReactNode;
  variant?: GlassVariant;
  hover?: boolean;
  className?: string;
}

export function Card({ children, variant = 'glass', hover = false, className }: CardProps) {
  return (
    <GlassSurface
      variant={variant}
      hover={hover}
      className={cn('rounded-2xl p-6', className)}
    >
      {children}
    </GlassSurface>
  );
}


/* -----------------------------------------------------------------------
   Badge / Tag
   Small pill labels for categories, statuses, capabilities.
   ----------------------------------------------------------------------- */

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'accent' | 'outline';
  className?: string;
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium tracking-wide',
        variant === 'default' && 'bg-white/[0.05] text-white/40',
        variant === 'outline' && 'border border-white/[0.08] text-white/30',
        className,
      )}
      style={
        variant === 'accent'
          ? {
              background: 'color-mix(in srgb, var(--color-accent) 12%, transparent)',
              color: 'var(--color-accent-hover)',
              border: '1px solid color-mix(in srgb, var(--color-accent) 25%, transparent)',
            }
          : undefined
      }
    >
      {children}
    </span>
  );
}

/* -----------------------------------------------------------------------
   Eyebrow
   The small uppercase label above every page hero and section heading.
   ----------------------------------------------------------------------- */

interface EyebrowProps {
  children: ReactNode;
  className?: string;
}

export function Eyebrow({ children, className }: EyebrowProps) {
  return (
    <p
      className={cn(
        'text-xs tracking-[0.2em] uppercase text-white/30',
        className,
      )}
    >
      {children}
    </p>
  );
}

/* -----------------------------------------------------------------------
   SectionHeading
   Title block with optional description. Uses serif-italic accent.
   ----------------------------------------------------------------------- */

interface SectionHeadingProps {
  title: string;
  accent?: string;
  description?: string;
  className?: string;
}

export function SectionHeading({
  title,
  accent,
  description,
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn('text-center', className)}>
      <h2 className="text-4xl md:text-5xl lg:text-6xl tracking-tight leading-[1.1]">
        {title}
        {accent && (
          <>
            {' '}
            <span className="font-serif italic text-white/35">{accent}</span>
          </>
        )}
      </h2>
      {description && (
        <p className="mt-5 text-base text-white/40 max-w-xl mx-auto leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
}

/* -----------------------------------------------------------------------
   Button Component
   Reusable CTA and SSO button. Supports hover lifting, loading, and success checkmarks.
   ----------------------------------------------------------------------- */

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'sso';
  isLoading?: boolean;
  isSuccess?: boolean;
  children: ReactNode;
}

export function Button({
  variant = 'primary',
  isLoading = false,
  isSuccess = false,
  disabled,
  children,
  className,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading || isSuccess}
      className={cn(
        'relative inline-flex items-center justify-center gap-2 rounded-lg text-sm font-semibold select-none cursor-pointer outline-none transition-all duration-300 w-full h-10 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none',
        variant === 'primary' && 'bg-[#4F8CFF]/12 border border-[#4F8CFF]/45 text-[#F8FAFC] hover:bg-[#4F8CFF]/22 hover:border-[#4F8CFF]/70 hover:shadow-[0_0_15px_rgba(79,140,255,0.25)]',
        variant === 'secondary' && 'bg-transparent border border-white/20 text-white/80 hover:bg-white/[0.04] hover:border-white/40 hover:text-white',
        variant === 'sso' && 'bg-transparent border border-white/12 text-white/70 hover:bg-white/[0.04] hover:border-white/30 hover:text-white',
        isSuccess && 'bg-success/80 border-transparent text-white hover:bg-success/80 hover:shadow-none',
        className
      )}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg className="w-4 h-4 animate-spin" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M9 1.5a7.5 7.5 0 1 1-5.3 2.2" />
          </svg>
          Authenticating
        </span>
      ) : isSuccess ? (
        <span className="flex items-center gap-1.5 animate-fade-in">
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="4 10 8 14 16 6"/>
          </svg>
          Welcome to Atlas
        </span>
      ) : (
        children
      )}
    </button>
  );
}

/* -----------------------------------------------------------------------
   Input Component
   Reusable Text and Password input field. Handles borders and focuses automatically.
   ----------------------------------------------------------------------- */

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  id: string;
  error?: string;
  trailingAction?: ReactNode;
}

export function Input({
  label,
  id,
  error,
  type = 'text',
  trailingAction,
  disabled,
  className,
  ...props
}: InputProps) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      <label className="text-[11px] font-semibold text-[#94A3B8] uppercase tracking-wider" htmlFor={id}>
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={type}
          disabled={disabled}
          className={cn(
            'w-full h-10 px-3.5 text-sm rounded-lg bg-transparent border transition-all duration-300 outline-none text-[#F8FAFC] placeholder:text-white/25',
            error 
              ? 'border-error/50 focus:border-error focus:shadow-[0_0_10px_rgba(239,68,68,0.15)] bg-error/[0.01]' 
              : 'border-white/15 focus:border-[#4F8CFF]/60 focus:bg-white/[0.04] focus:shadow-[0_0_12px_rgba(79,140,255,0.15)]',
            trailingAction ? 'pr-10' : '',
            className
          )}
          {...props}
        />
        {trailingAction && (
          <div className="absolute right-1 top-1/2 -translate-y-1/2">
            {trailingAction}
          </div>
        )}
      </div>
      {error && (
        <span className="text-[11px] text-error font-medium" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
