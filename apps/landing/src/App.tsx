import { Routes, Route, BrowserRouter } from 'react-router-dom';
import { ExperienceProvider } from '@/core/ExperienceController';
import { PublicLayout } from '@/layouts/PublicLayout';
import { WorkspaceLayout } from '@/layouts/WorkspaceLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

import { useExperience } from '@/core/ExperienceController';
import { MultiStepLoader } from '@/components/ui/multi-step-loader';

/* Marketing pages (lazy-loaded for perf) */
import { Component, lazy, Suspense, type ErrorInfo, type ReactNode } from 'react';
import { PageLoader } from '@/components/layout/PageLoader';

const Landing = lazy(() => import('@/pages/Landing'));
const Platform = lazy(() => import('@/pages/Platform'));
const Benchmarks = lazy(() => import('@/pages/Benchmarks'));
const Research = lazy(() => import('@/pages/Research'));
const Documentation = lazy(() => import('@/pages/Documentation'));
const OpenSource = lazy(() => import('@/pages/OpenSource'));
const Login = lazy(() => import('@/pages/Login'));
const Sandbox = lazy(() => import('@/components/ui/draggable-card-demo-2'));

/* Workspace */
const Workspace = lazy(() => import('@/pages/workspace/Workspace'));
const WorkspaceBenchmarks = lazy(() => import('@/pages/workspace/Benchmarks'));
const WorkspaceExperiments = lazy(() => import('@/pages/workspace/Experiments'));
const WorkspaceProviders = lazy(() => import('@/pages/workspace/Providers'));
const WorkspaceModels = lazy(() => import('@/pages/workspace/Models'));
const DatasetsPage = lazy(() => import('@/features/datasets/page/DatasetsPage'));
const WorkspaceSection = lazy(() => import('@/pages/workspace/WorkspaceSection'));
const WorkspaceNotFound = lazy(() => import('@/pages/workspace/WorkspaceNotFound'));

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

function AppRoutes() {
  console.log('[ATLAS ROUTER] App.tsx routes initialized');
  return (
    <Routes>
      {/* Marketing site — PublicLayout with cinematic Fabric */}
      <Route element={<PublicLayout />}>
        <Route index element={<Suspense fallback={<PageLoader />}><Landing /></Suspense>} />
        <Route path="platform" element={<Suspense fallback={<PageLoader />}><Platform /></Suspense>} />
        <Route path="benchmarks" element={<Suspense fallback={<PageLoader />}><Benchmarks /></Suspense>} />
        <Route path="research" element={<Suspense fallback={<PageLoader />}><Research /></Suspense>} />
        <Route path="documentation" element={<Suspense fallback={<PageLoader />}><Documentation /></Suspense>} />
        <Route path="open-source" element={<Suspense fallback={<PageLoader />}><OpenSource /></Suspense>} />
        <Route path="sandbox" element={<Suspense fallback={<PageLoader />}><Sandbox /></Suspense>} />
      </Route>

      {/* Auth page */}
      <Route path="login" element={<Suspense fallback={<PageLoader />}><Login /></Suspense>} />

      {/* Workspace — WorkspaceLayout with ambient Fabric */}
      <Route element={<ProtectedRoute />}>
        <Route path="dashboard" element={<WorkspaceLayout />}>
          <Route index element={<Suspense fallback={<PageLoader />}><Workspace /></Suspense>} />
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
          <Route path="settings" element={<Suspense fallback={<WorkspaceSection title="Settings" description="Configure your Workspace preferences." />}><WorkspaceSection title="Settings" description="Configure your Workspace preferences." /></Suspense>} />
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
      <Route path="*" element={<Suspense fallback={<PageLoader />}><Landing /></Suspense>} />
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
      <ExperienceProvider>
        <AppContainer />
      </ExperienceProvider>
    </BrowserRouter>
  );
}

export default App;
