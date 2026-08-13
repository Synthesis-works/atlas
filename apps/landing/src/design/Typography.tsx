/**
 * Atlas Design Language — Typography
 * Display, Heading, Body, and Caption primitives.
 * Instrument Serif is the signature italic accent built into Heading.
 */

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { ScrambleHeading, ScrambleSectionTitle, ScrambleText } from '@/components/motion';

/* -----------------------------------------------------------------------
   Display
   The hero-level heading. Used once per page, inside PageHero.
   ----------------------------------------------------------------------- */

interface DisplayProps {
  children: ReactNode;
  accent?: string;
  className?: string;
}

export function Display({ children, accent, className }: DisplayProps) {
  return (
    <ScrambleHeading
      text={typeof children === 'string' ? children : String(children)}
      className={cn(
        'text-5xl md:text-7xl lg:text-8xl font-semibold tracking-tight leading-[1.05]',
        className,
      )}
    >
      {accent && (
        <>
          {' '}
          <ScrambleText 
            text={accent}
            as="span"
            className="font-serif italic text-white/40"
          />
        </>
      )}
    </ScrambleHeading>
  );
}

/* -----------------------------------------------------------------------
   Heading
   Section-level heading. Supports an italic accent fragment.
   ----------------------------------------------------------------------- */

interface HeadingProps {
  children: ReactNode;
  as?: 'h2' | 'h3' | 'h4';
  accent?: string;
  className?: string;
}

const headingSizes = {
  h2: 'text-3xl md:text-5xl tracking-tight',
  h3: 'text-xl md:text-2xl tracking-tight',
  h4: 'text-base md:text-lg font-medium',
};

export function Heading({ children, as: Tag = 'h2', accent, className }: HeadingProps) {
  return (
    <ScrambleSectionTitle 
      text={typeof children === 'string' ? children : String(children)}
      as={Tag}
      className={cn(headingSizes[Tag], className)}
    >
      {accent && (
        <>
          {' '}
          <ScrambleText 
            text={accent}
            as="span"
            className="font-serif italic text-white/40"
          />
        </>
      )}
    </ScrambleSectionTitle>
  );
}

/* -----------------------------------------------------------------------
   Body
   Running text. Used for descriptions, paragraphs, explanations.
   ----------------------------------------------------------------------- */

interface BodyProps {
  children: ReactNode;
  className?: string;
}

export function Body({ children, className }: BodyProps) {
  return (
    <p className={cn('text-base text-text-secondary leading-relaxed', className)}>
      {children}
    </p>
  );
}

/* -----------------------------------------------------------------------
   Caption
   Small labels, metadata, timestamps, secondary info.
   ----------------------------------------------------------------------- */

interface CaptionProps {
  children: ReactNode;
  className?: string;
}

export function Caption({ children, className }: CaptionProps) {
  return (
    <span className={cn('text-sm text-text-quaternary', className)}>
      {children}
    </span>
  );
}
