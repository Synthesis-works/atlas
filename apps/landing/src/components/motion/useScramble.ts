import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';
import { useReducedMotion } from 'framer-motion';
import { animate, scrambleText } from 'animejs';
import { MotionTokens } from './tokens';
import type { ScramblePreset, ReplayStrategy } from './tokens';
import { useLocation } from 'react-router-dom';

export interface UseScrambleProps {
  text: string;
  duration?: number;
  delay?: number;
  speed?: number;
  chars?: string;
  preset?: ScramblePreset;
  once?: boolean;
  disabled?: boolean;
  replayStrategy?: ReplayStrategy;
}

export function useScramble(
  ref: RefObject<HTMLElement | null>,
  {
    text,
    duration = MotionTokens.durations.heading,
    delay = 0,
    speed,
    chars,
    preset = 'default',
    once = true,
    disabled = false,
    replayStrategy = 'once',
  }: UseScrambleProps
) {
  const prefersReducedMotion = useReducedMotion();
  const hasAnimated = useRef(false);
  const location = useLocation();
  const lastPathnameRef = useRef(location.pathname);
  const lastTextRef = useRef(text);

  // Derive replay strategy considering legacy 'once' prop
  const activeStrategy = (once && replayStrategy === 'once') ? 'once' : replayStrategy;

  useEffect(() => {
    if (text !== lastTextRef.current) {
      hasAnimated.current = false;
      lastTextRef.current = text;
    }
  }, [text]);

  useEffect(() => {
    if (activeStrategy === 'replayOnRoute' && location.pathname !== lastPathnameRef.current) {
      hasAnimated.current = false;
      lastPathnameRef.current = location.pathname;
    }
  }, [location.pathname, activeStrategy]);

  useEffect(() => {
    if (disabled || prefersReducedMotion) return;
    
    const element = ref.current;
    if (!element) return;

    let observer: IntersectionObserver | null = null;
    let animation: any = null;

    const playAnimation = () => {
      if (hasAnimated.current && activeStrategy === 'once') return;
      
      let characters = chars;
      if (!characters && preset !== 'custom') {
        characters = MotionTokens.presets[preset] || MotionTokens.presets.default;
      }

      animation = animate(element, {
        innerHTML: scrambleText({ text, chars: characters }),
        duration,
        delay,
        playbackRate: speed || 1, // utilize speed prop if provided
      });
      
      hasAnimated.current = true;
    };

    if (activeStrategy === 'replayOnVisibility') {
      observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            playAnimation();
          } else {
            // Reset state when it leaves view so it replays next time
            hasAnimated.current = false;
          }
        },
        { threshold: 0.1 }
      );
      observer.observe(element);
    } else {
      // For 'once' or 'replayOnRoute', we still want to wait until it's visible the FIRST time
      if (!hasAnimated.current) {
        observer = new IntersectionObserver(
          ([entry]) => {
            if (entry.isIntersecting) {
              playAnimation();
              if (observer) observer.disconnect();
            }
          },
          { threshold: 0.1 }
        );
        observer.observe(element);
      }
    }

    return () => {
      if (observer) observer.disconnect();
      if (animation) animation.pause();
    };
  }, [
    text, duration, delay, speed, chars, preset, disabled, 
    prefersReducedMotion, activeStrategy, ref
  ]);

  return { prefersReducedMotion };
}
