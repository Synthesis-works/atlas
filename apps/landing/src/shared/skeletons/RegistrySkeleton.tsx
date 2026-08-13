import React from 'react';

export const RegistrySkeleton: React.FC = () => {
  return (
    <div className="w-full rounded-xl border border-white/5 bg-black/40 p-4 space-y-4 animate-pulse">
      <div className="flex justify-between items-center pb-2 border-b border-white/5">
        <div className="w-32 h-4 rounded bg-white/10" />
        <div className="w-24 h-4 rounded bg-white/10" />
      </div>
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex justify-between items-center py-2.5 border-b border-white/[0.02]">
          <div className="w-40 h-4 rounded bg-white/10" />
          <div className="w-16 h-3 rounded bg-white/5" />
          <div className="w-24 h-3 rounded bg-white/5" />
          <div className="w-12 h-3 rounded bg-white/10" />
        </div>
      ))}
    </div>
  );
};

export default RegistrySkeleton;
