import { createContext, useContext, useRef, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { MotionTokens } from './tokens';
import { useLocation } from 'react-router-dom';

interface MotionContextType {
  registerHeading: () => number;
}

const MotionContext = createContext<MotionContextType | null>(null);

export function MotionProvider({ children }: { children: ReactNode }) {
  const counterRef = useRef(0);
  const location = useLocation();

  // Reset stagger counter on route change
  useEffect(() => {
    // We defer the reset slightly so any components unmounting don't mess up the new components mounting
    const timeout = setTimeout(() => {
       counterRef.current = 0;
    }, 50);
    return () => clearTimeout(timeout);
  }, [location.pathname]);

  const registerHeading = useCallback(() => {
    const delay = counterRef.current * MotionTokens.stagger.baseDelayMs;
    counterRef.current++;
    return delay;
  }, []);

  return (
    <MotionContext.Provider value={{ registerHeading }}>
      {children}
    </MotionContext.Provider>
  );
}

export function useStaggerDelay(manualDelay?: number) {
  const context = useContext(MotionContext);
  const localRef = useRef<number | null>(null);

  if (localRef.current === null) {
    if (manualDelay !== undefined) {
      localRef.current = manualDelay;
    } else if (context) {
      localRef.current = context.registerHeading();
    } else {
      localRef.current = 0;
    }
  }

  return localRef.current;
}
