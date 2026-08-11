import React from 'react';

export const KPISkeleton: React.FC = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="p-5 rounded-2xl border border-white/5 bg-black/40 h-28 flex flex-col justify-between">
          <div className="flex justify-between items-center">
            <div className="w-20 h-3 rounded bg-white/10" />
            <div className="w-6 h-6 rounded-full bg-white/10" />
          </div>
          <div className="w-16 h-7 rounded bg-white/10" />
          <div className="w-24 h-2 rounded bg-white/5" />
        </div>
      ))}
    </div>
  );
};

export default KPISkeleton;
