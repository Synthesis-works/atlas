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

/* Agent Workspace */
const AgentLayout = lazy(() => import('@/pages/workspace/agent/AgentLayout'));
const AgentDashboard = lazy(() => import('@/pages/workspace/agent/AgentDashboard'));
const AgentWorkspaceRun = lazy(() => import('@/pages/workspace/agent/AgentWorkspaceRun'));
const AgentReportPage = lazy(() => import('@/pages/workspace/agent/AgentReportPage'));

class AppErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Atlas route failed to render', error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="relative min-h-screen w-full overflow-hidden flex items-center justify-center bg-black font-sans">
        <img src="/loader-bg.jpg" alt="" className="absolute inset-0 w-full h-full object-cover opacity-70" />
        <div className="absolute inset-0 bg-black/65 backdrop-blur-md" />
        <div className="relative z-10 flex flex-col items-center gap-4 text-center px-6">
          <p className="text-xs uppercase tracking-[0.2em] text-white/40">Atlas could not open this view</p>
          <button type="button" onClick={() => window.location.reload()} className="rounded-lg border border-white/10 bg-white/[0.06] px-4 py-2 text-xs text-white/75 hover:bg-white/[0.1] transition-colors">
            Reload view
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
          
          {/* Agent Workspace Routes */}
          <Route path="agent" element={<Suspense fallback={<PageLoader />}><AgentLayout /></Suspense>}>
            <Route index element={<Suspense fallback={<PageLoader />}><AgentDashboard /></Suspense>} />
            <Route path="run/:taskId" element={<Suspense fallback={<PageLoader />}><AgentWorkspaceRun /></Suspense>} />
            <Route path="report/:reportId" element={<Suspense fallback={<PageLoader />}><AgentReportPage /></Suspense>} />
          </Route>
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
