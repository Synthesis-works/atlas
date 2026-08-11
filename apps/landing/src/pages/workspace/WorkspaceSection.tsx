/**
 * WorkspaceSection — compact frontend-only module surfaces for workspace areas
 * that do not yet have a dedicated feature implementation.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { pageCrossfade } from '@/lib/motion';
import { Badge, Card } from '@/design/primitives';
import { ScrambleHeading, ScrambleSectionTitle } from '@/components/motion';
import {
  ArrowUpRight,
  Database,
  FileText,
  Plus,
  Settings2,
  Trophy,
  type LucideIcon,
} from 'lucide-react';

interface WorkspaceSectionProps {
  title: string;
  description?: string;
}

interface ModuleConfig {
  icon: LucideIcon;
  eyebrow: string;
  primaryAction: string;
  metrics: { label: string; value: string; detail: string }[];
  items: { title: string; meta: string; status: string }[];
}

const MODULES: Record<string, ModuleConfig> = {
  Datasets: {
    icon: Database,
    eyebrow: 'Data Registry',
    primaryAction: 'Import dataset',
    metrics: [
      { label: 'Registered datasets', value: '24', detail: '3 updated this week' },
      { label: 'Validated samples', value: '1.8M', detail: '99.6% schema coverage' },
      { label: 'Storage used', value: '42 GB', detail: '58 GB available' },
    ],
    items: [
      { title: 'MMLU-Pro Test v2', meta: '16,000 samples · v2.1.0', status: 'Validated' },
      { title: 'SWE-bench Verified', meta: '500 tasks · v1.0.3', status: 'Validated' },
      { title: 'GPQA Diamond', meta: '448 questions · v1.2.0', status: 'Reviewing' },
      { title: 'HumanEval-Plus', meta: '164 tasks · v1.1.0', status: 'Ready' },
    ],
  },
  Reports: {
    icon: FileText,
    eyebrow: 'Report Library',
    primaryAction: 'Generate report',
    metrics: [
      { label: 'Generated reports', value: '40', detail: '6 since Monday' },
      { label: 'Shared externally', value: '12', detail: '2 awaiting review' },
      { label: 'Scheduled', value: '4', detail: 'Next run in 3 hours' },
    ],
    items: [
      { title: 'Q3 Quality Review', meta: 'GPT-5 · MMLU-Pro · 4 min ago', status: 'Ready' },
      { title: 'Safety Regression Audit', meta: 'Llama 4 Maverick · Yesterday', status: 'Draft' },
      { title: 'Provider Cost Analysis', meta: 'All registered models · Yesterday', status: 'Ready' },
      { title: 'Weekly Evaluation Digest', meta: 'Workspace summary · Jul 18', status: 'Scheduled' },
    ],
  },
  Leaderboard: {
    icon: Trophy,
    eyebrow: 'Capability Rankings',
    primaryAction: 'Create comparison',
    metrics: [
      { label: 'Ranked models', value: '18', detail: 'Across 8 benchmark families' },
      { label: 'Top composite score', value: '91.8', detail: 'GPT-5 · +1.4 this week' },
      { label: 'New results', value: '36', detail: 'In the last 24 hours' },
    ],
    items: [
      { title: 'GPT-5', meta: '91.8 composite · 12 benchmark suites', status: '#1' },
      { title: 'Claude 3.5 Sonnet', meta: '89.4 composite · 11 benchmark suites', status: '#2' },
      { title: 'Gemini 2.0 Flash', meta: '87.1 composite · 10 benchmark suites', status: '#3' },
      { title: 'Llama 3.1 405B', meta: '84.6 composite · 9 benchmark suites', status: '#4' },
    ],
  },
  Settings: {
    icon: Settings2,
    eyebrow: 'Workspace Preferences',
    primaryAction: 'Save preferences',
    metrics: [
      { label: 'Active members', value: '8', detail: '3 online now' },
      { label: 'Connected providers', value: '4', detail: 'All systems operational' },
      { label: 'Automations', value: '6', detail: '2 scheduled today' },
    ],
    items: [
      { title: 'Notifications', meta: 'Evaluation alerts and weekly summaries', status: 'Enabled' },
      { title: 'Default evaluation runtime', meta: 'Atlas runner · GPU standard', status: 'Configured' },
      { title: 'Data retention', meta: 'Evaluation artifacts retained for 90 days', status: 'Configured' },
      { title: 'Workspace access', meta: 'SSO required for all collaborators', status: 'Secure' },
    ],
  },
};

export default function WorkspaceSection({ title, description }: WorkspaceSectionProps) {
  const config = MODULES[title] ?? MODULES.Datasets;
  const Icon = config.icon;
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  return (
    <motion.div
      variants={pageCrossfade}
      initial="initial"
      animate="animate"
      exit="exit"
      className="p-4 sm:p-6 lg:p-7 max-w-[1440px] mx-auto w-full space-y-6"
    >
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-white/35">
            <Icon className="h-3.5 w-3.5 text-accent/80" />
            {config.eyebrow}
          </div>
          <ScrambleHeading text={title} className="mt-2 text-2xl font-semibold tracking-tight text-white" />
          <p className="mt-1 text-sm text-white/40">{description}</p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-3.5 py-2 text-xs font-medium text-accent-hover transition-colors hover:bg-accent/20">
          <Plus className="h-3.5 w-3.5" />
          {config.primaryAction}
        </button>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {config.metrics.map((metric) => (
          <Card key={metric.label} className="!rounded-lg !p-4">
            <p className="text-xs text-white/35">{metric.label}</p>
            <p className="mt-2 text-2xl leading-none font-semibold tracking-tight text-white tabular-nums">{metric.value}</p>
            <p className="mt-2 text-[11px] text-white/30">{metric.detail}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <Card className="xl:col-span-8 !rounded-lg !p-0 overflow-hidden">
          <div className="flex items-center justify-between gap-3 px-4 sm:px-5 py-3.5 border-b border-white/[0.06]">
            <div>
              <ScrambleSectionTitle text="Current workspace items" className="text-sm font-medium text-white" />
              <p className="mt-0.5 text-xs text-white/30">Updated from the local evaluation registry</p>
            </div>
            <button className="p-2 text-white/35 hover:text-white transition-colors" aria-label="Open all items">
              <ArrowUpRight className="h-4 w-4" />
            </button>
          </div>
          <div className="divide-y divide-white/[0.05]">
            {config.items.map((item) => (
              <button key={item.title} className="w-full flex items-center justify-between gap-4 px-4 sm:px-5 py-3.5 text-left hover:bg-white/[0.025] transition-colors">
                <div className="min-w-0">
                  <p className="text-sm text-white/80 truncate">{item.title}</p>
                  <p className="mt-1 text-xs text-white/30 truncate">{item.meta}</p>
                </div>
                <Badge variant="outline" className="shrink-0 !px-2.5 !py-0.5 !text-[10px]">{item.status}</Badge>
              </button>
            ))}
          </div>
        </Card>

        <aside className="xl:col-span-4 space-y-3">
          <Card className="!rounded-lg !p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-white/35">Workspace health</p>
            <div className="mt-4 flex items-end justify-between">
              <div>
                <p className="text-3xl font-semibold tracking-tight text-white">99.98%</p>
                <p className="mt-1 text-xs text-white/30">Availability in the last 30 days</p>
              </div>
              <span className="flex h-9 w-9 items-center justify-center rounded-full border border-emerald-400/25 bg-emerald-400/10">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
              </span>
            </div>
          </Card>

          {title === 'Settings' && (
            <Card className="!rounded-lg !p-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-white/80">Evaluation notifications</p>
                  <p className="mt-1 text-xs text-white/30">Alert the workspace when runs change state.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setNotificationsEnabled((enabled) => !enabled)}
                  aria-pressed={notificationsEnabled}
                  aria-label="Toggle evaluation notifications"
                  className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${notificationsEnabled ? 'bg-accent' : 'bg-white/10'}`}
                >
                  <span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-transform ${notificationsEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>
            </Card>
          )}
        </aside>
      </div>
    </motion.div>
  );
}
