/**
 * Store — Workspace Central Store
 * Synchronizes reactive state across Benchmarks, Evaluations, Queue, Runtime, and UI Preferences.
 */

import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { Benchmark, BenchmarkCategory } from '@/domain/benchmarks/types';
import { MOCK_BENCHMARKS } from '@/domain/benchmarks/mock';
import type { WidgetLayoutState } from '@/design/glass/types';

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: string;
}

export interface QueueItem {
  id: string;
  model: string;
  benchmarkName: string;
  progress: number;
  status: 'Running' | 'Queued' | 'Completed' | 'Failed';
}

export interface WorkspaceUserPreferences {
  viewMode: 'grid' | 'list';
  compactMode: boolean;
  pinnedIds: string[];
}

interface WorkspaceStoreContextType {
  benchmarks: Benchmark[];
  searchQuery: string;
  selectedCategory: BenchmarkCategory | 'all';
  activeDrawerBenchmark: Benchmark | null;
  compareBenchmarkIds: string[];
  preferences: WorkspaceUserPreferences;
  queue: QueueItem[];
  terminalLogs: string[];
  notifications: NotificationItem[];
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (cat: BenchmarkCategory | 'all') => void;
  setActiveDrawerBenchmark: (bm: Benchmark | null) => void;
  toggleCompareBenchmark: (id: string) => void;
  clearCompareBenchmarks: () => void;
  toggleViewMode: () => void;
  togglePinBenchmark: (id: string) => void;
  triggerEvaluationRun: (benchmarkId: string, model: string) => void;
  addNotification: (title: string, message: string, type?: NotificationItem['type']) => void;
  dismissNotification: (id: string) => void;
  widgetLayouts: Record<string, WidgetLayoutState>;
  updateWidgetLayout: (id: string, layout: Partial<WidgetLayoutState>) => void;
  resetWidgetLayouts: () => void;
}

const WorkspaceStoreContext = createContext<WorkspaceStoreContextType | null>(null);

const INITIAL_QUEUE: QueueItem[] = [
  { id: 'q-1', model: 'GPT-5', benchmarkName: 'MMLU-Pro', progress: 78, status: 'Running' },
  { id: 'q-2', model: 'Claude-3.5-Sonnet', benchmarkName: 'GPQA', progress: 41, status: 'Running' },
  { id: 'q-3', model: 'Qwen-2.5-Coder', benchmarkName: 'HumanEval', progress: 0, status: 'Queued' },
  { id: 'q-4', model: 'Gemma-2-27B', benchmarkName: 'Arena-Hard', progress: 100, status: 'Completed' },
];

const INITIAL_LOGS = [
  '09:42:01 [System] Initializing Atlas Evaluation Engine v2.1...',
  '09:42:02 [Dataset] MMLU-Pro test split indexed (16,000 samples).',
  '09:42:04 [Engine] Connected model engine target: GPT-5 (stream=enabled).',
  '09:42:08 [Execution] Evaluated prompt batch 314 / 1200 (Pass@1: 92.8%).',
  '09:42:15 [Metrics] Calculating hallucination rate and latency metrics...',
  '09:42:18 [Report] Artifacts saved to /evaluations/run-148/artifacts.',
];

export const WorkspaceStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>(MOCK_BENCHMARKS);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<BenchmarkCategory | 'all'>('all');
  const [activeDrawerBenchmark, setActiveDrawerBenchmark] = useState<Benchmark | null>(null);
  const [compareBenchmarkIds, setCompareBenchmarkIds] = useState<string[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>(INITIAL_QUEUE);
  const [terminalLogs, setTerminalLogs] = useState<string[]>(INITIAL_LOGS);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [preferences, setPreferences] = useState<WorkspaceUserPreferences>({
    viewMode: 'grid',
    compactMode: false,
    pinnedIds: ['mmlu-pro', 'humaneval'],
  });

  const [widgetLayouts, setWidgetLayouts] = useState<Record<string, WidgetLayoutState>>(() => {
    try {
      const saved = localStorage.getItem('atlas_widget_layouts');
      if (saved) return JSON.parse(saved);
    } catch (_) {}

    return {
      assistant: {
        x: window.innerWidth > 900 ? window.innerWidth - 380 : 40,
        y: 120,
        width: 340,
        height: 380,
        visible: false,
        collapsed: true,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      notes: {
        x: 80,
        y: 350,
        width: 300,
        height: 240,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      terminal: {
        x: 100,
        y: 180,
        width: 500,
        height: 320,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      queue: {
        x: 140,
        y: 400,
        width: 320,
        height: 240,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      palette: {
        x: 40,
        y: 120,
        width: 240,
        height: 100,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      }
    };
  });

  const updateWidgetLayout = useCallback((id: string, layout: Partial<WidgetLayoutState>) => {
    setWidgetLayouts((prev) => {
      const next = {
        ...prev,
        [id]: {
          ...prev[id],
          ...layout,
        },
      };
      try {
        localStorage.setItem('atlas_widget_layouts', JSON.stringify(next));
      } catch (_) {}
      return next;
    });
  }, []);

  const resetWidgetLayouts = useCallback(() => {
    const next = {
      assistant: {
        x: window.innerWidth > 900 ? window.innerWidth - 380 : 40,
        y: 120,
        width: 340,
        height: 380,
        visible: false,
        collapsed: true,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      notes: {
        x: 80,
        y: 350,
        width: 300,
        height: 240,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      terminal: {
        x: 100,
        y: 180,
        width: 500,
        height: 320,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      queue: {
        x: 140,
        y: 400,
        width: 320,
        height: 240,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      },
      palette: {
        x: 40,
        y: 120,
        width: 240,
        height: 100,
        visible: false,
        collapsed: false,
        minimized: false,
        dragging: false,
        focused: false,
        locked: false,
      }
    };
    setWidgetLayouts(next);
    try {
      localStorage.setItem('atlas_widget_layouts', JSON.stringify(next));
    } catch (_) {}
  }, []);

  const toggleViewMode = useCallback(() => {
    setPreferences((prev) => ({
      ...prev,
      viewMode: prev.viewMode === 'grid' ? 'list' : 'grid',
    }));
  }, []);

  const togglePinBenchmark = useCallback((id: string) => {
    setPreferences((prev) => {
      const exists = prev.pinnedIds.includes(id);
      return {
        ...prev,
        pinnedIds: exists ? prev.pinnedIds.filter((p) => p !== id) : [...prev.pinnedIds, id],
      };
    });
  }, []);

  const toggleCompareBenchmark = useCallback((id: string) => {
    setCompareBenchmarkIds((prev) => {
      if (prev.includes(id)) return prev.filter((i) => i !== id);
      if (prev.length >= 4) return prev; // max 4 for comparison
      return [...prev, id];
    });
  }, []);

  const clearCompareBenchmarks = useCallback(() => {
    setCompareBenchmarkIds([]);
  }, []);

  const addNotification = useCallback(
    (title: string, message: string, type: NotificationItem['type'] = 'info') => {
      const newItem: NotificationItem = {
        id: `notif-${Date.now()}`,
        title,
        message,
        type,
        timestamp: new Date().toLocaleTimeString(),
      };
      setNotifications((prev) => [newItem, ...prev.slice(0, 4)]);
    },
    []
  );

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const triggerEvaluationRun = useCallback(
    (benchmarkId: string, model: string) => {
      const bm = benchmarks.find((b) => b.id === benchmarkId);
      if (!bm) return;

      const newJobId = `q-${Date.now()}`;
      const newQueueItem: QueueItem = {
        id: newJobId,
        model,
        benchmarkName: bm.name,
        progress: 5,
        status: 'Running',
      };

      setQueue((prev) => [newQueueItem, ...prev]);

      // Update benchmark status to Running in state
      setBenchmarks((prev) =>
        prev.map((b) => (b.id === benchmarkId ? { ...b, status: 'Running' } : b))
      );

      const timestamp = new Date().toLocaleTimeString();
      setTerminalLogs((prev) => [
        `${timestamp} [Job] Triggered evaluation for ${bm.name} on ${model}...`,
        ...prev,
      ]);

      addNotification(
        'Evaluation Started',
        `Running ${bm.name} evaluation against ${model}`,
        'info'
      );
    },
    [benchmarks, addNotification]
  );

  const value = useMemo(
    () => ({
      benchmarks,
      searchQuery,
      selectedCategory,
      activeDrawerBenchmark,
      compareBenchmarkIds,
      preferences,
      queue,
      terminalLogs,
      notifications,
      setSearchQuery,
      setSelectedCategory,
      setActiveDrawerBenchmark,
      toggleCompareBenchmark,
      clearCompareBenchmarks,
      toggleViewMode,
      togglePinBenchmark,
      triggerEvaluationRun,
      addNotification,
      dismissNotification,
      widgetLayouts,
      updateWidgetLayout,
      resetWidgetLayouts,
    }),
    [
      benchmarks,
      searchQuery,
      selectedCategory,
      activeDrawerBenchmark,
      compareBenchmarkIds,
      preferences,
      queue,
      terminalLogs,
      notifications,
      toggleCompareBenchmark,
      clearCompareBenchmarks,
      toggleViewMode,
      togglePinBenchmark,
      triggerEvaluationRun,
      addNotification,
      dismissNotification,
      widgetLayouts,
      updateWidgetLayout,
      resetWidgetLayouts,
    ]
  );

  return (
    <WorkspaceStoreContext.Provider value={value}>{children}</WorkspaceStoreContext.Provider>
  );
};

export const useWorkspaceStore = () => {
  const context = useContext(WorkspaceStoreContext);
  if (!context) {
    throw new Error('useWorkspaceStore must be used within a WorkspaceStoreProvider');
  }
  return context;
};
