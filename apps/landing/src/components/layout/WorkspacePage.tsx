import React from 'react';
import { LayoutTokens } from '@/design/layout';
import { cn } from '@/lib/utils';

interface WorkspacePageProps {
  children: React.ReactNode;
  className?: string;
}

export function WorkspacePage({ children, className }: WorkspacePageProps) {
  return (
    <div className={cn("w-full py-12 pb-32", LayoutTokens.sectionGap, className)}>
      {children}
    </div>
  );
}

interface WorkspaceHeroProps {
  children: React.ReactNode;
  className?: string;
}

export function WorkspaceHero({ children, className }: WorkspaceHeroProps) {
  return (
    <header className={cn('flex flex-col md:flex-row md:items-center md:justify-between gap-4 shrink-0', className)}>
      <div className="space-y-1.5 flex-1 min-w-0">
        {children}
      </div>
    </header>
  );
}

interface WorkspaceToolbarProps {
  children: React.ReactNode;
  className?: string;
}

export function WorkspaceToolbar({ children, className }: WorkspaceToolbarProps) {
  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-3 shrink-0', className)}>
      {children}
    </div>
  );
}

interface WorkspaceKPIsProps {
  children: React.ReactNode;
  className?: string;
}

export function WorkspaceKPIs({ children, className }: WorkspaceKPIsProps) {
  return (
    <section className={cn('w-full', className)}>
      {children}
    </section>
  );
}

interface WorkspaceSectionProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export function WorkspaceAnalytics({ children, className, title }: WorkspaceSectionProps) {
  return (
    <section className={cn('w-full', className)}>
      {title && <h3 className="text-xs font-mono font-semibold text-white/50 mb-3 px-1">{title}</h3>}
      {children}
    </section>
  );
}

export function WorkspaceOperations({ children, className, title }: WorkspaceSectionProps) {
  return (
    <section className={cn('w-full', className)}>
      {title && <h3 className="text-xs font-mono font-semibold text-white/50 mb-3 px-1">{title}</h3>}
      {children}
    </section>
  );
}

export function WorkspaceRegistry({ children, className, title }: WorkspaceSectionProps) {
  return (
    <section className={cn('w-full flex-1 flex flex-col min-h-0', className)}>
      {title && <h3 className="text-xs font-mono font-semibold text-white/50 mb-3 px-1">{title}</h3>}
      <div className="flex-1 flex flex-col min-h-0">
        {children}
      </div>
    </section>
  );
}
