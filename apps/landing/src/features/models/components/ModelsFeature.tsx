import { motion } from 'framer-motion';
import { pageCrossfade } from '@/lib/motion';
import { ModelsStoreProvider } from '../store/modelsStore';
import { FleetHealthHero } from './FleetHealthHero';
import { FleetInsights } from './FleetInsights';
import { ModelRecommendation } from './ModelRecommendation';
import { FleetTopology } from './FleetTopology';
import { ModelsRegistry } from './ModelsRegistry';
import { PerformanceAnalytics } from './PerformanceAnalytics';
import { CostAnalytics } from './CostAnalytics';
import { ModelDrawer } from './ModelDrawer';
import { FleetCommandPalette } from './FleetCommandPalette';
import {
  WorkspacePage,
  WorkspaceHero,
  WorkspaceAnalytics,
  WorkspaceOperations,
  WorkspaceRegistry,
} from '@/components/layout/WorkspacePage';

function ModelsWorkspaceContent() {
  return (
    <>
      <motion.div
        variants={pageCrossfade}
        initial="initial"
        animate="animate"
        exit="exit"
      >
        <WorkspacePage className="space-y-3.5">
          {/* Stage 1: Awareness — Fleet Health Summary Hero & AI Insights */}
          <WorkspaceHero className="space-y-3.5">
            <FleetHealthHero />
            <FleetInsights />
          </WorkspaceHero>

          {/* Stage 2: Decision — Model Intelligence Recommendation Engine */}
          <WorkspaceAnalytics>
            <ModelRecommendation />
          </WorkspaceAnalytics>

          {/* Stage 3: Execution — Signature Infrastructure Topology Graph & Operations */}
          <WorkspaceOperations className="space-y-3.5">
            <FleetTopology />
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 items-stretch">
              <PerformanceAnalytics />
              <CostAnalytics />
            </div>
          </WorkspaceOperations>

          {/* Stage 4: Control — Control Plane Registry */}
          <WorkspaceRegistry>
            <ModelsRegistry />
          </WorkspaceRegistry>
        </WorkspacePage>
      </motion.div>

      {/* Deep Operational Inspector Drawer */}
      <ModelDrawer />

      {/* Signature Ctrl+K Fleet Command Palette */}
      <FleetCommandPalette />
    </>
  );
}

export default function ModelsFeature() {
  return (
    <ModelsStoreProvider>
      <ModelsWorkspaceContent />
    </ModelsStoreProvider>
  );
}
