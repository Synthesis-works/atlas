/**
 * Workspace Layout — the OS chrome
 *
 * Distinct from marketing: sidebar navigation, topbar, ambient Intelligence
 * Fabric. All copy says "Workspace" — never "Dashboard".
 */

import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { WorkspaceStoreProvider } from '@/store/workspaceStore';
import {
  LayoutDashboard,
  Database,
  FolderKanban,
  FileText,
  BarChart3,
  Settings,
  LogOut,
  Cpu,
  Server,
  FlaskConical,
} from 'lucide-react';
import { useExperience } from '@/core/ExperienceController';
import { MotionProvider, ScrambleHeading } from '@/components/motion';
import { FloatingDock } from '@/components/ui/floating-dock';
import { WorkspaceWidgets } from '@/features/workspace/widgets/WorkspaceWidgets';
import { WorkspaceLauncher } from '@/components/ui/WorkspaceLauncher';

import { getAuthToken } from '@/core/api/client';

/** Derive page title from pathname for the topbar */
function getPageTitle(pathname: string): string {
  const segment = pathname.split('/').at(-1) ?? '';
  if (!segment || segment === 'dashboard') return 'Overview';
  return segment.charAt(0).toUpperCase() + segment.slice(1);
}

export function WorkspaceLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setPageTransitionKey, exitAtlas } = useExperience();
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const token = getAuthToken();
    const isLoggedIn = Boolean(token) || localStorage.getItem('atlas_logged_in') === 'true';
    if (!isLoggedIn) {
      navigate('/', { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
    setPageTransitionKey(location.pathname);
    mainRef.current?.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, [location.pathname, setPageTransitionKey]);

  const pageTitle = getPageTitle(location.pathname);

  const dockItems = [
    {
      title: 'Overview',
      icon: <LayoutDashboard className="w-full h-full" />,
      href: '/dashboard',
    },
    {
      title: 'Datasets',
      icon: <FolderKanban className="w-full h-full" />,
      href: '/dashboard/datasets',
    },
    {
      title: 'Models',
      icon: <Cpu className="w-full h-full" />,
      href: '/dashboard/models',
    },
    {
      title: 'Benchmarks',
      icon: <Database className="w-full h-full" />,
      href: '/dashboard/benchmarks',
    },
    {
      title: 'Providers',
      icon: <Server className="w-full h-full" />,
      href: '/dashboard/providers',
    },
    {
      title: 'Experiments',
      icon: <FlaskConical className="w-full h-full" />,
      href: '/dashboard/experiments',
    },
    {
      title: 'Reports',
      icon: <FileText className="w-full h-full" />,
      href: '/dashboard/reports',
    },
    {
      title: 'Leaderboard',
      icon: <BarChart3 className="w-full h-full" />,
      href: '/dashboard/leaderboard',
    },
    {
      title: 'Agent',
      icon: <span className="w-full h-full text-accent font-bold" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem'}}>✦</span>,
      href: '/dashboard/agent',
    },
    {
      title: 'Settings',
      icon: <Settings className="w-full h-full" />,
      href: '/dashboard/settings',
    },
  ];

  return (
    <WorkspaceStoreProvider>
      <MotionProvider>
      <div className="relative min-h-screen bg-ink-2 text-white flex flex-col overflow-hidden">
      {/* Topbar */}
      <header
        className="h-14 shrink-0 border-b border-border/80 flex items-center px-6 gap-3 z-20 bg-ink-1/80 backdrop-blur-sm"
      >
        {/* Atlas logo + Workspace wordmark */}
        <div className="flex items-center gap-2 px-2">
          {/* Atlas logomark — inline SVG matches the Navbar version */}
          <svg width="16" height="16" viewBox="0 0 28 28" fill="none" className="text-accent shrink-0" aria-hidden="true">
            <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="14" cy="11" r="2.5" fill="currentColor" opacity="0.15" />
              <circle cx="14" cy="11" r="2.5" />
              <line x1="14" y1="8.5" x2="7" y2="24" />
              <line x1="14" y1="8.5" x2="21" y2="24" />
              <line x1="9.5" y1="18" x2="18.5" y2="18" />
              <line x1="14" y1="8.5" x2="14" y2="3" />
              <line x1="14" y1="11" x2="6" y2="7" />
              <line x1="14" y1="11" x2="22" y2="7" />
              <circle cx="14" cy="3" r="1.25" />
              <circle cx="6" cy="7" r="1.25" />
              <circle cx="22" cy="7" r="1.25" />
            </g>
          </svg>
          <span className="text-sm font-semibold tracking-tight text-white/80">Atlas</span>
          <span className="text-[10px] text-white/20 ml-2 tracking-wider uppercase hidden sm:block">Workspace</span>
        </div>

        <div className="h-4 w-px bg-white/10 mx-2 hidden sm:block" />

        <ScrambleHeading text={pageTitle} className="text-sm font-medium text-white/60" delay={0} />

        <nav aria-label="Workspace navigation" className="hidden lg:flex items-center gap-1 ml-auto">
          {dockItems.map((item) => (
            <NavLink
              key={item.title}
              to={item.href}
              title={item.title}
              aria-label={item.title}
              className={({ isActive }) =>
                `flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
                  isActive
                    ? 'bg-accent/15 text-accent-hover border border-accent/25'
                    : 'text-white/35 hover:bg-white/[0.05] hover:text-white/75 border border-transparent'
                }`
              }
            >
              <span className="h-4 w-4">{item.icon}</span>
            </NavLink>
          ))}
        </nav>

        {/* Exit Workspace */}
        <button
          onClick={exitAtlas}
          className="ml-auto lg:ml-3 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-white/40 hover:text-white/80 border border-white/5 hover:border-white/10 bg-white/[0.02] transition-colors cursor-pointer"
          aria-label="Leave Workspace and return to marketing site"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Exit Workspace</span>
        </button>
      </header>

      {/* Main content area */}
      <div className="relative flex-1 z-10 flex flex-col min-h-0 overflow-hidden">
        {/* Page content — crossfade on route change */}
        <main ref={mainRef} className="flex-1 overflow-y-auto pb-28 min-h-0">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="h-full"
          >
            <div className="w-full max-w-[1600px] mx-auto px-4 md:px-6 xl:px-8 h-full">
              <Outlet />
            </div>
          </motion.div>
        </main>
      </div>

      {/* Floating Dock Navigation */}
      <div className="fixed bottom-5 inset-x-0 flex justify-center z-30 pointer-events-none">
        <div className="pointer-events-auto">
          <FloatingDock items={dockItems} />
        </div>
      </div>

      {/* Floating workspace widgets (persistent across tab changes) */}
      <WorkspaceWidgets />

      {/* Global Workspace Launcher (Cmd+K) */}
      <WorkspaceLauncher />
      </div>
      </MotionProvider>
    </WorkspaceStoreProvider>
  );
}
