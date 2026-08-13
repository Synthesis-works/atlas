import React from 'react';

export const DrawerSkeleton: React.FC = () => {
  return (
    <div className="space-y-6 p-4 animate-pulse">
      <div className="w-48 h-6 rounded bg-white/10" />
      <div className="w-full h-24 rounded-xl bg-white/5" />
      <div className="grid grid-cols-2 gap-3">
        <div className="h-16 rounded-xl bg-white/5" />
        <div className="h-16 rounded-xl bg-white/5" />
      </div>
      <div className="w-full h-36 rounded-xl bg-white/5" />
    </div>
  );
};

export default DrawerSkeleton;
