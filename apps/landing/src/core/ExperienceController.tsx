/**
 * Atlas Experience Controller
 *
 * The conductor of the orchestra. Orchestrates global experience state so
 * every visual element — the Intelligence Fabric, layouts, transitions,
 * page animations — listens to one source of truth instead of talking to
 * each other directly.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export type ExperienceMode = 'marketing' | 'transition' | 'workspace';
export type FabricMode = 'cinematic' | 'ambient';
export type TransitionPhase = 'idle' | 'dissolve' | 'reorganize' | 'materialize' | 'settle';

export interface ExperienceState {
  experienceMode: ExperienceMode;
  fabricMode: FabricMode;
  transitionPhase: TransitionPhase;
  prefersReducedMotion: boolean;
  pageTransitionKey: string;
  loaderActive: boolean;
  loaderStates: { text: string }[];
  loaderDuration: number;
}

export interface ExperienceActions {
  enterAtlas: () => void;
  exitAtlas: () => void;
  setReducedMotion: (v: boolean) => void;
  setPageTransitionKey: (key: string) => void;
  startLoader: (states: { text: string }[], duration: number, callback: () => void) => void;
  handleLoaderComplete: () => void;
}

type ExperienceContext = ExperienceState & ExperienceActions;

const ctx = createContext<ExperienceContext | null>(null);

export function useExperience(): ExperienceContext {
  const value = useContext(ctx);
  if (!value) throw new Error('useExperience must be used inside <ExperienceProvider>');
  return value;
}

export function ExperienceProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();

  const [experienceMode, setExperienceMode] = useState<ExperienceMode>('marketing');
  const [transitionPhase, setTransitionPhase] = useState<TransitionPhase>('idle');
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [pageTransitionKey, setPageTransitionKey] = useState('');

  // Loader state
  const [loaderActive, setLoaderActive] = useState(false);
  const [loaderStates, setLoaderStates] = useState<{ text: string }[]>([]);
  const [loaderDuration, setLoaderDuration] = useState(1000);
  const [loaderCallback, setLoaderCallback] = useState<(() => void) | null>(null);

  /* Sync workspace/marketing mode with route (skip during boundary crossing) */
  useEffect(() => {
    if (transitionPhase !== 'idle') return;
    setExperienceMode(location.pathname.startsWith('/dashboard') ? 'workspace' : 'marketing');
  }, [location.pathname, transitionPhase]);

  useEffect(() => {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  const fabricMode = useMemo<FabricMode>(() => {
    if (experienceMode === 'workspace') return 'ambient';
    return 'cinematic';
  }, [experienceMode]);

  const enterAtlas = useCallback(() => {
    if (transitionPhase !== 'idle' || experienceMode === 'workspace') return;

    if (prefersReducedMotion) {
      setExperienceMode('workspace');
      navigate('/dashboard');
      return;
    }

    setTransitionPhase('dissolve');
    setTimeout(() => {
      setTransitionPhase('reorganize');
      setExperienceMode('transition');
      setTimeout(() => {
        setTransitionPhase('materialize');
        navigate('/dashboard');
        setTimeout(() => {
          setExperienceMode('workspace');
          setTransitionPhase('settle');
          setTimeout(() => setTransitionPhase('idle'), 400);
        }, 600);
      }, 600);
    }, 500);
  }, [transitionPhase, experienceMode, prefersReducedMotion, navigate]);

  const exitAtlas = useCallback(() => {
    localStorage.removeItem('atlas_logged_in');
    setExperienceMode('marketing');
    navigate('/');
  }, [navigate]);

  const startLoader = useCallback((states: { text: string }[], duration: number, callback: () => void) => {
    setLoaderStates(states);
    setLoaderDuration(duration);
    setLoaderActive(true);
    setLoaderCallback(() => callback);
  }, []);

  const handleLoaderComplete = useCallback(() => {
    setLoaderActive(false);
    if (loaderCallback) {
      loaderCallback();
      setLoaderCallback(null);
    }
  }, [loaderCallback]);

  const value = useMemo<ExperienceContext>(
    () => ({
      experienceMode,
      fabricMode,
      transitionPhase,
      prefersReducedMotion,
      pageTransitionKey,
      loaderActive,
      loaderStates,
      loaderDuration,
      enterAtlas,
      exitAtlas,
      setReducedMotion: setPrefersReducedMotion,
      setPageTransitionKey,
      startLoader,
      handleLoaderComplete,
    }),
    [
      experienceMode,
      fabricMode,
      transitionPhase,
      prefersReducedMotion,
      pageTransitionKey,
      loaderActive,
      loaderStates,
      loaderDuration,
      enterAtlas,
      exitAtlas,
      startLoader,
      handleLoaderComplete,
    ],
  );

  return <ctx.Provider value={value}>{children}</ctx.Provider>;
}
