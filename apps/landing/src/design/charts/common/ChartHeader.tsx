/**
 * ChartHeader & ChartToolbar — Card titles, badges, and controls.
 */

import React from 'react';

export const ChartHeader: React.FC<{
  title: string;
  subtitle?: string;
  badge?: string;
}> = ({ title, subtitle, badge }) => (
  <div className="flex items-start justify-between mb-4">
    <div>
      <h4 className="text-sm font-semibold text-white tracking-tight">{title}</h4>
      {subtitle && <p className="text-xs text-white/40 leading-relaxed mt-0.5">{subtitle}</p>}
    </div>
    {badge && (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium text-accent bg-accent/10 border border-accent/20">
        {badge}
      </span>
    )}
  </div>
);

export const ChartToolbar: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="flex items-center gap-2 mb-3">{children}</div>
);
