/**
 * CardFlip — Atlas Design Language primitive
 *
 * Compound flip-card with proper 3D CSS and robust interaction model.
 *
 * Interaction:
 *  - Desktop (pointer:fine):  hover enters → flip; leave → unflip.
 *  - Touch (pointer:coarse):  tap → toggle. Tap again or tap elsewhere → unflip.
 *  - Keyboard: focus flips, blur unflips; Enter/Space also toggles.
 *  - prefers-reduced-motion: faces swap instantly with no rotation.
 *
 * Fixes applied vs original:
 *  - Removed useExperience dependency (reads matchMedia directly — no context needed)
 *  - Fixed pointer-type detection so hover-flip doesn't fight tap-toggle on touch
 *  - Fixed backface-visibility applied via style= not className (cross-browser)
 *  - Fixed the inner preserve-3d container missing h-full
 *  - Fixed bg-ink-3/40 Tailwind opacity modifier (use inline style instead)
 *  - Removed conflicting onFocus/onBlur flip that re-triggers on child interactions
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
  type KeyboardEvent,
} from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

/* ----------------------------------------------------------------------- */
/*  Reduced-motion detection — reads OS preference directly, no context     */
/* ----------------------------------------------------------------------- */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false,
  );
  useEffect(() => {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);
  return reduced;
}

/* ----------------------------------------------------------------------- */
/*  Pointer-fine detection — true on mouse/trackpad, false on touch screens */
/* ----------------------------------------------------------------------- */
function useIsPointerFine(): boolean {
  const [fine, setFine] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia('(pointer:fine)').matches
      : true,
  );
  useEffect(() => {
    const mql = window.matchMedia('(pointer:fine)');
    const handler = (e: MediaQueryListEvent) => setFine(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);
  return fine;
}

/* ----------------------------------------------------------------------- */
/*  Context                                                                  */
/* ----------------------------------------------------------------------- */
interface CardFlipCtx {
  isFlipped: boolean;
  reduced: boolean;
}

const Ctx = createContext<CardFlipCtx | null>(null);

function useCtx(name: string): CardFlipCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error(`<${name}> must be inside <CardFlip>`);
  return v;
}

/* ----------------------------------------------------------------------- */
/*  Shared face styles                                                       */
/* ----------------------------------------------------------------------- */
const FACE_BASE = {
  position: 'absolute' as const,
  inset: 0,
  backfaceVisibility: 'hidden' as const,
  WebkitBackfaceVisibility: 'hidden' as const,
  borderRadius: 'inherit',
  overflow: 'hidden' as const,
  height: '100%',
  width: '100%',
};

const GLASS_STYLE = {
  background: 'linear-gradient(180deg, rgba(14,14,22,0.22) 0%, rgba(14,14,22,0.32) 100%)',
  backdropFilter: 'blur(28px) saturate(160%)',
  WebkitBackdropFilter: 'blur(28px) saturate(160%)',
  boxShadow: `
    0 24px 60px rgba(0,0,0,0.40),
    inset 0 1px 1px rgba(255,255,255,0.40),
    inset 0 -6px 16px rgba(255,255,255,0.05),
    0 0 0 1px rgba(255,255,255,0.10)
  `,
};

const GLASS_BACK_EXTRA = {
  boxShadow: `
    0 24px 60px rgba(0,0,0,0.45),
    inset 0 1px 1px rgba(255,255,255,0.50),
    inset 0 -8px 20px rgba(255,255,255,0.06),
    0 0 0 1px rgba(255,255,255,0.18),
    0 0 24px rgba(99,102,241,0.12)
  `,
};

/* ----------------------------------------------------------------------- */
/*  CardFlip.Front                                                           */
/* ----------------------------------------------------------------------- */
interface FrontProps {
  children: ReactNode;
  className?: string;
}

function CardFlipFront({ children, className }: FrontProps) {
  const { isFlipped, reduced } = useCtx('CardFlip.Front');

  return (
    <div
      aria-hidden={isFlipped}
      style={{
        ...FACE_BASE,
        ...GLASS_STYLE,
        transform: reduced
          ? undefined
          : `perspective(1200px) rotateY(${isFlipped ? -180 : 0}deg)`,
        transition: reduced ? undefined : 'transform 0.7s cubic-bezier(0.65,0,0.35,1)',
        willChange: 'transform',
        zIndex: isFlipped ? 0 : 1,
        opacity: reduced ? (isFlipped ? 0 : 1) : 1,
        pointerEvents: isFlipped ? 'none' : 'auto',
      }}
      className={cn('flex flex-col', className)}
    >
      {children}
    </div>
  );
}

/* ----------------------------------------------------------------------- */
/*  CardFlip.Back                                                            */
/* ----------------------------------------------------------------------- */
interface BackProps {
  title: string;
  description?: string;
  features?: string[];
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
  children?: ReactNode;
}

function CardFlipBack({ title, description, features, actionLabel, onAction, className, children }: BackProps) {
  const { isFlipped, reduced } = useCtx('CardFlip.Back');

  return (
    <div
      aria-hidden={!isFlipped}
      style={{
        ...FACE_BASE,
        ...GLASS_STYLE,
        ...GLASS_BACK_EXTRA,
        transform: reduced
          ? undefined
          : `perspective(1200px) rotateY(${isFlipped ? 0 : 180}deg)`,
        transition: reduced ? undefined : 'transform 0.7s cubic-bezier(0.65,0,0.35,1)',
        willChange: 'transform',
        zIndex: isFlipped ? 1 : 0,
        opacity: reduced ? (isFlipped ? 1 : 0) : 1,
        pointerEvents: isFlipped ? 'auto' : 'none',
      }}
      className={cn('flex flex-col p-5', className)}
    >
      {/* Header */}
      <div className="shrink-0 mb-3">
        <h4 className="text-sm font-semibold text-white tracking-tight mb-1">{title}</h4>
        {description && (
          <p className="text-[11px] text-white/45 leading-relaxed">{description}</p>
        )}
      </div>

      {/* Features list */}
      {features && features.length > 0 && (
        <div className="flex-1 min-h-0 overflow-y-auto space-y-1.5 pr-0.5">
          {features.map((f, i) => (
            <div
              key={f}
              className="flex items-center gap-2 text-xs text-white/55"
              style={{
                transform: isFlipped ? 'translateX(0)' : 'translateX(-8px)',
                opacity: isFlipped ? 1 : 0,
                transition: `transform 300ms cubic-bezier(0.23,1,0.32,1) ${i * 45 + 160}ms,
                             opacity 280ms ease ${i * 45 + 160}ms`,
              }}
            >
              <ArrowRight className="w-3 h-3 shrink-0" style={{ color: 'var(--color-accent)' }} />
              <span>{f}</span>
            </div>
          ))}
        </div>
      )}

      {children}

      {/* CTA */}
      {actionLabel && (
        <div className="shrink-0 mt-4 pt-3 border-t border-white/[0.07]">
          <button
            type="button"
            tabIndex={isFlipped ? 0 : -1}
            onClick={(e) => { e.stopPropagation(); onAction?.(); }}
            className="group/cta w-full flex items-center justify-between px-2.5 py-2 rounded-xl
                       bg-white/[0.03] hover:bg-accent/10 transition-colors duration-200 cursor-pointer"
          >
            <span className="text-xs font-medium text-white/70 group-hover/cta:text-white transition-colors">
              {actionLabel}
            </span>
            <ArrowRight className="w-3.5 h-3.5 text-accent group-hover/cta:translate-x-0.5 transition-transform" />
          </button>
        </div>
      )}
    </div>
  );
}

/* ----------------------------------------------------------------------- */
/*  CardFlip root                                                            */
/* ----------------------------------------------------------------------- */
interface CardFlipProps {
  children: ReactNode;
  className?: string;
  minHeight?: string;
}

function CardFlipRoot({ children, className, minHeight = 'h-[300px]' }: CardFlipProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const reduced    = usePrefersReducedMotion();
  const isFine     = useIsPointerFine();
  const rootRef    = useRef<HTMLDivElement>(null);

  const flip   = useCallback(() => setIsFlipped(true),  []);
  const unflip = useCallback(() => setIsFlipped(false), []);
  const toggle = useCallback(() => setIsFlipped(v => !v), []);

  /* Close when clicking outside (touch devices) */
  useEffect(() => {
    if (!isFlipped) return;
    const handler = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setIsFlipped(false);
      }
    };
    document.addEventListener('pointerdown', handler);
    return () => document.removeEventListener('pointerdown', handler);
  }, [isFlipped]);

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    if (e.key === 'Escape') unflip();
  };

  return (
    <Ctx.Provider value={{ isFlipped, reduced }}>
      <div
        ref={rootRef}
        tabIndex={0}
        role="button"
        aria-label={isFlipped ? 'Flip back' : 'Flip card for details'}
        className={cn(
          'relative w-full cursor-pointer select-none outline-none',
          'focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:ring-offset-2',
          'focus-visible:ring-offset-transparent rounded-2xl',
          minHeight,
          className,
        )}
        /* Desktop: hover to flip */
        onMouseEnter={isFine ? flip : undefined}
        onMouseLeave={isFine ? unflip : undefined}
        /* Touch / keyboard: click/tap to toggle */
        onClick={!isFine ? toggle : undefined}
        onKeyDown={handleKeyDown}
      >
        {/*
          preserve-3d container — must be h-full so both faces fill the card.
          Do NOT add overflow:hidden here — that breaks 3D transforms in Safari.
        */}
        <div
          className="relative h-full w-full"
          style={{ transformStyle: 'preserve-3d' }}
        >
          {children}
        </div>
      </div>
    </Ctx.Provider>
  );
}

/* ----------------------------------------------------------------------- */
/*  Compound export                                                          */
/* ----------------------------------------------------------------------- */
type CardFlipType = typeof CardFlipRoot & {
  Front: typeof CardFlipFront;
  Back:  typeof CardFlipBack;
};

const CardFlip = CardFlipRoot as CardFlipType;
CardFlip.Front = CardFlipFront;
CardFlip.Back  = CardFlipBack;

export { CardFlip };
