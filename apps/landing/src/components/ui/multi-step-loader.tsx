import { cn } from '@/lib/utils';
import { AnimatePresence, motion } from 'framer-motion';
import { useState, useEffect } from 'react';

const CheckIcon = ({ className }: { className?: string }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
      className={cn("w-5 h-5", className)}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
};

const CheckFilled = ({ className }: { className?: string }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={cn("w-5 h-5", className)}
    >
      <path
        fillRule="evenodd"
        d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
        clipRule="evenodd"
      />
    </svg>
  );
};

type LoadingState = {
  text: string;
};

const LoaderCore = ({
  loadingStates,
  value = 0,
}: {
  loadingStates: LoadingState[];
  value?: number;
}) => {
  return (
    <div className="relative max-w-xl mx-auto w-full h-[180px] overflow-hidden flex flex-col justify-center select-none">
      <motion.div
        animate={{ y: 70 - value * 44 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="absolute left-0 right-0 flex flex-col gap-1"
      >
        {loadingStates.map((loadingState, index) => {
          const distance = Math.abs(index - value);
          const opacity = Math.max(1 - distance * 0.3, 0.08);

          return (
            <div
              key={index}
              className="text-left flex gap-3 h-10 items-center justify-start transition-opacity duration-300"
              style={{ opacity }}
            >
              <div className="shrink-0">
                {index > value && (
                  <CheckIcon className="text-white/20" />
                )}
                {index <= value && (
                  <CheckFilled
                    className={cn(
                      "text-white/40",
                      value === index && "text-accent opacity-100 animate-pulse"
                    )}
                  />
                )}
              </div>
              <span
                className={cn(
                  "text-white/30 text-sm md:text-base font-normal tracking-wide transition-all duration-300",
                  value === index && "text-white opacity-100 font-medium scale-[1.01]"
                )}
              >
                {loadingState.text}
              </span>
            </div>
          );
        })}
      </motion.div>
    </div>
  );
};

export const MultiStepLoader = ({
  loadingStates,
  loading,
  duration = 2000,
  loop = true,
  onComplete,
}: {
  loadingStates: LoadingState[];
  loading?: boolean;
  duration?: number;
  loop?: boolean;
  onComplete?: () => void;
}) => {
  const [currentState, setCurrentState] = useState(0);

  useEffect(() => {
    setCurrentState(0);
  }, [loading, loadingStates]);

  useEffect(() => {
    if (!loading || loadingStates.length === 0) {
      setCurrentState(0);
      return;
    }

    if (currentState === loadingStates.length - 1 && !loop) {
      const timeout = setTimeout(() => {
        onComplete?.();
      }, duration);
      return () => clearTimeout(timeout);
    }

    const timeout = setTimeout(() => {
      setCurrentState((prevState) =>
        loop
          ? prevState === loadingStates.length - 1
            ? 0
            : prevState + 1
          : Math.min(prevState + 1, loadingStates.length - 1)
      );
    }, duration);

    return () => clearTimeout(timeout);
  }, [currentState, loading, loop, loadingStates.length, duration, onComplete]);

  return (
    <AnimatePresence mode="wait">
      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="w-full h-full fixed inset-0 z-[100] flex items-center justify-center bg-black font-sans overflow-hidden"
        >
          {/* Background image — clean and visible */}
          <img
            src="/loader-bg.jpg"
            alt="Loading background"
            className="absolute inset-0 w-full h-full object-cover z-0 select-none pointer-events-none"
          />
          {/* Subtle dark overlay for contrast */}
          <div className="absolute inset-0 bg-black/45 z-10 pointer-events-none" />

          {/* Centered steps list — floating with no border box */}
          <div className="relative z-30 w-full max-w-sm px-6">
            <LoaderCore value={currentState} loadingStates={loadingStates} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
