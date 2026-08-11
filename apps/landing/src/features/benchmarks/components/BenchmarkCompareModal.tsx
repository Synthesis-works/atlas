import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2 } from 'lucide-react';
import type { Benchmark } from '@/domain/benchmarks/types';
import { StatusBadge } from '@/shared/components';

interface BenchmarkCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  benchmarks: Benchmark[];
  onRemove: (id: string) => void;
}

export const BenchmarkCompareModal: React.FC<BenchmarkCompareModalProps> = ({
  isOpen,
  onClose,
  benchmarks,
  onRemove,
}) => {
  if (!isOpen || benchmarks.length === 0) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/75 backdrop-blur-md z-40"
        />

        {/* Modal Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="relative z-50 w-full max-w-5xl rounded-2xl border border-white/10 bg-neutral-950 p-6 shadow-2xl space-y-6"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-white/5">
            <div>
              <h3 className="text-lg font-bold text-white tracking-tight">Benchmark Side-by-Side Comparison</h3>
              <p className="text-xs text-white/40 mt-0.5">Comparing {benchmarks.length} benchmark specifications</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Comparison Grid */}
          <div className="overflow-x-auto">
            <div className={`grid grid-cols-${benchmarks.length + 1} gap-4 min-w-[600px] text-xs font-mono`}>
              {/* Row 1: Names */}
              <div className="font-semibold text-white/40 py-2">Benchmark</div>
              {benchmarks.map((bm) => (
                <div key={bm.id} className="p-3 rounded-xl bg-white/[0.03] border border-white/5 space-y-1 relative">
                  <button
                    onClick={() => onRemove(bm.id)}
                    className="absolute top-2 right-2 text-white/30 hover:text-rose-400"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                  <div className="font-bold text-white text-sm truncate">{bm.name}</div>
                  <div className="text-[10px] text-white/40">v{bm.version}</div>
                </div>
              ))}

              {/* Category */}
              <div className="font-semibold text-white/40 py-2">Category</div>
              {benchmarks.map((bm) => (
                <div key={bm.id} className="py-2 text-white/80 uppercase font-mono">{bm.category}</div>
              ))}

              {/* Status */}
              <div className="font-semibold text-white/40 py-2">Status</div>
              {benchmarks.map((bm) => (
                <div key={bm.id} className="py-2"><StatusBadge status={bm.status} /></div>
              ))}

              {/* Tasks / Samples */}
              <div className="font-semibold text-white/40 py-2">Tasks / Samples</div>
              {benchmarks.map((bm) => (
                <div key={bm.id} className="py-2 text-white/80">{bm.tasksCount.toLocaleString()} / {bm.samplesCount.toLocaleString()}</div>
              ))}

              {/* Verification */}
              <div className="font-semibold text-white/40 py-2">Verification Score</div>
              {benchmarks.map((bm) => (
                <div key={bm.id} className="py-2 flex items-center gap-1.5 text-emerald-400 font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{bm.verificationScore}%</span>
                </div>
              ))}

              {/* Estimated Runtime */}
              <div className="font-semibold text-white/40 py-2">Estimated Runtime</div>
              {benchmarks.map((bm) => (
                <div key={bm.id} className="py-2 text-white/80">{bm.estimatedRuntime}</div>
              ))}

              {/* License */}
              <div className="font-semibold text-white/40 py-2">License</div>
              {benchmarks.map((bm) => (
                <div key={bm.id} className="py-2 text-white/70">{bm.license}</div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default BenchmarkCompareModal;
