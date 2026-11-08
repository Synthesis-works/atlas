import { Routes, Route, BrowserRouter, Navigate } from 'react-router-dom';
import { ExperienceProvider } from '@/core/ExperienceController';
import { AuthProvider } from '@/features/auth/AuthProvider';
import { MarketingRedirect } from '@/components/MarketingRedirect';
import { WorkspaceLayout } from '@/layouts/WorkspaceLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

import { useExperience } from '@/core/ExperienceController';
import { MultiStepLoader } from '@/components/ui/multi-step-loader';

/* Product pages (lazy-loaded for perf) */
import { Component, lazy, Suspense, type ErrorInfo, type ReactNode } from 'react';
import { PageLoader } from '@/components/layout/PageLoader';

const AgentLanding = lazy(() => import('@/pages/AgentLanding'));
const Login = lazy(() => import('@/pages/Login'));

/* Workspace */
const WorkspaceBenchmarks = lazy(() => import('@/pages/workspace/Benchmarks'));
const WorkspaceExperiments = lazy(() => import('@/pages/workspace/Experiments'));
const WorkspaceProviders = lazy(() => import('@/pages/workspace/Providers'));
const WorkspaceModels = lazy(() => import('@/pages/workspace/Models'));
const DatasetsPage = lazy(() => import('@/features/datasets/page/DatasetsPage'));
const BillingPage = lazy(() => import('@/features/billing/pages/BillingPage'));
const WorkspaceSection = lazy(() => import('@/pages/workspace/WorkspaceSection'));
const WorkspaceNotFound = lazy(() => import('@/pages/workspace/WorkspaceNotFound'));

/* Agent Workspace */
const AgentLayout = lazy(() => import('@/pages/workspace/agent/AgentLayout'));
const AgentDashboard = lazy(() => import('@/pages/workspace/agent/AgentDashboard'));
const AgentWorkspaceRun = lazy(() => import('@/pages/workspace/agent/AgentWorkspaceRun'));
const AgentReportPage = lazy(() => import('@/pages/workspace/agent/AgentReportPage'));

class AppErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: Error | null }> {
  state: { hasError: boolean; error: Error | null } = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): { hasError: boolean; error: Error } {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Atlas route failed to render', error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="relative min-h-screen w-full overflow-hidden flex items-center justify-center bg-black font-sans p-6">
        <div className="relative z-10 max-w-md w-full bg-zinc-900/90 border border-red-500/30 rounded-xl p-6 text-center space-y-4 shadow-2xl backdrop-blur-xl">
          <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto text-red-400 font-bold">
            !
          </div>
          <h2 className="text-lg font-semibold text-white">Atlas View Render Error</h2>
          <p className="text-xs text-white/60 font-mono bg-black/40 p-3 rounded border border-white/5 break-all text-left">
            {this.state.error?.message || 'An unexpected rendering exception occurred inside the workspace component tree.'}
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="w-full py-2.5 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-medium text-xs transition-colors"
          >
            Reload Atlas Engine
          </button>
        </div>
      </div>
    );
  }
}

/** Blank white fallback so the public front page doesn't flash the dark app loader. */
const LandingFallback = () => <div style={{ minHeight: '100vh', background: '#ffffff' }} />;

function AppRoutes() {
  console.log('[ATLAS ROUTER] App.tsx routes initialized');
  return (
    <Routes>
      {/* Public front page: has its own header and footer, so it sits outside PublicLayout */}
      <Route path="/" element={<Suspense fallback={<LandingFallback />}><AgentLanding /></Suspense>} />
      {/* The old in-app Home now lives on the front page, also served at this URL so the
          existing /dashboard/home link keeps working (public, so no login needed) */}
      <Route path="dashboard/home" element={<Suspense fallback={<LandingFallback />}><AgentLanding /></Suspense>} />

      {/* The marketing pages now live on the Synthesis Works organisation site.
          Keep their old paths working by forwarding them, with the same path,
          to the other origin. */}
      {['platform', 'benchmarks', 'research', 'documentation', 'cli', 'cli/install', 'open-source', 'sandbox'].map(
        (path) => <Route key={path} path={path} element={<MarketingRedirect />} />,
      )}

      {/* Auth page */}
      <Route path="login" element={<Suspense fallback={<PageLoader />}><Login /></Suspense>} />

      {/* Workspace — WorkspaceLayout with ambient Fabric */}
      <Route element={<ProtectedRoute />}>
        <Route path="dashboard" element={<WorkspaceLayout />}>
          {/* The agent is the product, so the dashboard opens on it */}
          <Route index element={<Navigate to="agent" replace />} />
          <Route path="benchmarks" element={<Suspense fallback={<PageLoader />}><WorkspaceBenchmarks /></Suspense>} />
          <Route path="datasets" element={<Suspense fallback={<PageLoader />}><DatasetsPage /></Suspense>} />
          
          {/* Clean Evaluations Route Group */}
          <Route path="evaluations">
            <Route index element={<Suspense fallback={<PageLoader />}><WorkspaceExperiments /></Suspense>} />
            <Route path="new" element={<Suspense fallback={<PageLoader />}><WorkspaceExperiments openNewModal={true} /></Suspense>} />
            <Route path="*" element={<Suspense fallback={<PageLoader />}><WorkspaceExperiments /></Suspense>} />
          </Route>

          <Route path="experiments" element={<Suspense fallback={<PageLoader />}><WorkspaceExperiments /></Suspense>} />
          <Route path="providers" element={<Suspense fallback={<PageLoader />}><WorkspaceProviders /></Suspense>} />
          <Route path="models" element={<Suspense fallback={<PageLoader />}><WorkspaceModels /></Suspense>} />
          <Route path="reports" element={<Suspense fallback={<WorkspaceSection title="Reports" description="View and compare evaluation reports." />}><WorkspaceSection title="Reports" description="View and compare evaluation reports." /></Suspense>} />
          <Route path="leaderboard" element={<Suspense fallback={<WorkspaceSection title="Leaderboard" description="Compare model rankings across capabilities." />}><WorkspaceSection title="Leaderboard" description="Compare model rankings across capabilities." /></Suspense>} />
          <Route path="billing" element={<Suspense fallback={<PageLoader />}><BillingPage /></Suspense>} />
          <Route path="settings" element={<Suspense fallback={<WorkspaceSection title="Settings" description="Configure your Workspace preferences." />}><WorkspaceSection title="Settings" description="Configure your Workspace preferences." /></Suspense>} />
{/* Agent Workspace Routes */}
          <Route path="agent" element={<Suspense fallback={<PageLoader />}><AgentLayout /></Suspense>}>
            <Route index element={<Suspense fallback={<PageLoader />}><AgentDashboard /></Suspense>} />
            <Route path="run/:taskId" element={<Suspense fallback={<PageLoader />}><AgentWorkspaceRun /></Suspense>} />
            <Route path="report/:reportId" element={<Suspense fallback={<PageLoader />}><AgentReportPage /></Suspense>} />
          </Route>
          <Route path="*" element={<Suspense fallback={<PageLoader />}><WorkspaceNotFound /></Suspense>} />
        </Route>
      </Route>
      
      {/* Dev Diagnostic Endpoint */}
      {import.meta.env.DEV && (
        <Route
          path="__atlas_dev"
          element={
            <div className="min-h-screen bg-black text-emerald-400 font-mono p-8 space-y-4">
              <h1 className="text-xl font-bold border-b border-emerald-500/20 pb-2">Atlas Frontend Diagnostic</h1>
              <div className="space-y-1 text-sm text-white/80">
                <p><span className="text-emerald-400">Environment:</span> development</p>
                <p><span className="text-emerald-400">Worktree:</span> wire_real_llm_adapter</p>
                <p><span className="text-emerald-400">Host:</span> 127.0.0.1</p>
                <p><span className="text-emerald-400">Port:</span> 5173</p>
              </div>
            </div>
          }
        />
      )}

      {/* Catch-all fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function AppContainer() {
  const { loaderActive, loaderStates, loaderDuration, handleLoaderComplete } = useExperience();

  return (
    <>
      <AppErrorBoundary>
        <AppRoutes />
      </AppErrorBoundary>
      <MultiStepLoader
        loadingStates={loaderStates}
        loading={loaderActive}
        duration={loaderDuration}
        loop={false}
        onComplete={handleLoaderComplete}
      />
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ExperienceProvider>
          <AppContainer />
        </ExperienceProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
