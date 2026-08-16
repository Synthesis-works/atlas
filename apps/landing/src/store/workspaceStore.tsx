/**
 * Store — Workspace Central Store
 * Synchronizes reactive state across Benchmarks, Evaluations, Queue, Runtime, and UI Preferences.
 */

import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import type { Benchmark, BenchmarkCategory } from '@/domain/benchmarks/types';
import { MOCK_BENCHMARKS } from '@/domain/benchmarks/mock';
import type { WidgetLayoutState } from '@/design/glass/types';
import { getBenchmarks } from '@/features/benchmarks/services/benchmarkService';
import { getEvaluations } from '@/features/evaluations/services/evaluationService';
import { executionPollingService } from '@/features/evaluations/services/executionPollingService';
import type { AgentTask } from '@/features/agent/types';
import { agentPollingService } from '@/features/agent/services/agentPollingService';

import { cancelExecution } from '@/features/evaluations/services/evaluationService';

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
  agentTasks: AgentTask[];
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
  cancelEvaluationRun: (executionId: string) => Promise<void>;
  addNotification: (title: string, message: string, type?: NotificationItem['type']) => void;
  dismissNotification: (id: string) => void;
  widgetLayouts: Record<string, WidgetLayoutState>;
  updateWidgetLayout: (id: string, layout: Partial<WidgetLayoutState>) => void;
  resetWidgetLayouts: () => void;
  setAgentTasks: React.Dispatch<React.SetStateAction<AgentTask[]>>;
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
  const [agentTasks, setAgentTasks] = useState<AgentTask[]>([]);
  const [terminalLogs, setTerminalLogs] = useState<string[]>(INITIAL_LOGS);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [preferences, setPreferences] = useState<WorkspaceUserPreferences>({
    viewMode: 'grid',
    compactMode: false,
    pinnedIds: ['mmlu-pro', 'humaneval'],
  });

  useEffect(() => {

    let isMounted = true;
    getBenchmarks().then((res) => {
      if (isMounted && res.data && res.data.length > 0) {
        setBenchmarks(res.data);
      }
    });
    getEvaluations().then((res) => {
      if (isMounted && res.data && res.data.length > 0) {
        const queueMapped: QueueItem[] = res.data.map((ev) => ({
          id: ev.id,
          model: ev.model,
          benchmarkName: ev.benchmark,
          progress: ev.progress,
          status: ev.status === 'Completed' ? 'Completed' : (ev.status === 'Failed' ? 'Failed' : (ev.status === 'Queued' ? 'Queued' : 'Running')),
        }));
        setQueue(queueMapped);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);


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
    async (benchmarkId: string, model: string) => {
      const bm = benchmarks.find((b) => b.id === benchmarkId);
      if (!bm) return;

      const timestamp = new Date().toLocaleTimeString();
      setTerminalLogs((prev) => [
        `${timestamp} [Job] Dispatching API execution for ${bm.name} on ${model}...`,
        ...prev,
      ]);

      const { dispatchExecution } = await import('@/features/evaluations/services/evaluationService');
      const res = await dispatchExecution(benchmarkId, model);

      const execId = res.data?.id || `q-${Date.now()}`;
      const initialStatus = (res.data?.status || 'Queued') as any;

      const newQueueItem: QueueItem = {
        id: execId,
        model,
        benchmarkName: bm.name,
        progress: 0,
        status: initialStatus === 'QUEUED' ? 'Queued' : initialStatus,
      };

      setQueue((prev) => [newQueueItem, ...prev.filter((q) => q.id !== execId)]);

      setBenchmarks((prev) =>
        prev.map((b) => (b.id === benchmarkId ? { ...b, status: 'Running' } : b))
      );

      setTerminalLogs((prev) => [
        `${new Date().toLocaleTimeString()} [Job ${execId}] Dispatched execution task. Status: ${initialStatus}`,
        ...prev,
      ]);

      addNotification(
        'Evaluation Queued',
        `Dispatched ${bm.name} execution (${execId.substring(0, 8)}) against ${model}`,
        'info'
      );
    },
    [benchmarks, addNotification]
  );

  const cancelEvaluationRun = useCallback(
    async (executionId: string) => {
      const timestamp = new Date().toLocaleTimeString();
      setTerminalLogs((prev) => [
        `${timestamp} [Job ${executionId}] Sending cancellation request...`,
        ...prev,
      ]);

      await cancelExecution(executionId);

      setQueue((prev) =>
        prev.map((item) =>
          item.id === executionId ? { ...item, status: 'Failed', progress: item.progress } : item
        )
      );

      setTerminalLogs((prev) => [
        `${new Date().toLocaleTimeString()} [Job ${executionId}] Execution cancelled by user. State: CANCELLED.`,
        ...prev,
      ]);

      addNotification('Execution Cancelled', `Execution ${executionId.substring(0, 8)} was cancelled.`, 'warning');
    },
    [addNotification]
  );

  useEffect(() => {
    const activeIds = queue
      .filter((q) => q.status === 'Queued' || q.status === 'Running')
      .map((q) => q.id);

    if (activeIds.length > 0) {
      executionPollingService.registerActiveExecutions(activeIds);
    }

    const unsubscribe = executionPollingService.subscribe((updates) => {
      setQueue((prevQueue) =>
        prevQueue.map((item) => {
          const match = updates.find((u) => u.id === item.id);
          if (!match) return item;

          let mappedStatus: QueueItem['status'] = 'Running';
          if (match.status === 'QUEUED') mappedStatus = 'Queued';
          else if (match.status === 'COMPLETED') mappedStatus = 'Completed';
          else if (['FAILED', 'FAILED_PERMANENT', 'CANCELLED', 'TIMED_OUT'].includes(match.status)) {
            mappedStatus = 'Failed';
          }

          const progress =
            match.total_items && match.total_items > 0
              ? Math.round(((match.completed_items || 0) / match.total_items) * 100)
              : item.progress;

          return {
            ...item,
            status: mappedStatus,
            progress,
          };
        })
      );
    });

    return () => unsubscribe();
  }, [queue]);

  useEffect(() => {
    const activeIds = agentTasks
      .filter((t) => t.status !== 'COMPLETED' && t.status !== 'FAILED' && t.status !== 'CANCELLED')
      .map((t) => t.task_id);

    if (activeIds.length > 0) {
      agentPollingService.registerActiveTasks(activeIds);
    }

    const unsubscribe = agentPollingService.subscribe((updates) => {
      setAgentTasks((prevTasks) => {
        let changed = false;
        const newTasks = prevTasks.map((task) => {
          const update = updates.find((u) => u.task_id === task.task_id);
          if (update) {
            changed = true;
            return update;
          }
          return task;
        });
        
        // Also append any new tasks from the updates that weren't in prevTasks
        updates.forEach(update => {
          if (!prevTasks.find(t => t.task_id === update.task_id)) {
            newTasks.push(update);
            changed = true;
          }
        });
        
        return changed ? newTasks : prevTasks;
      });
    });

    return () => unsubscribe();
  }, [agentTasks]);

  const value = useMemo(
    () => ({
      benchmarks,
      searchQuery,
      selectedCategory,
      activeDrawerBenchmark,
      compareBenchmarkIds,
      preferences,
      queue,
      agentTasks,
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
      cancelEvaluationRun,
      addNotification,
      dismissNotification,
      widgetLayouts,
      updateWidgetLayout,
      resetWidgetLayouts,
      setAgentTasks,
    }),
    [
      benchmarks,
      searchQuery,
      selectedCategory,
      activeDrawerBenchmark,
      compareBenchmarkIds,
      preferences,
      queue,
      agentTasks,
      terminalLogs,
      notifications,
      toggleCompareBenchmark,
      clearCompareBenchmarks,
      toggleViewMode,
      togglePinBenchmark,
      triggerEvaluationRun,
      cancelEvaluationRun,
      addNotification,
      dismissNotification,
      widgetLayouts,
      updateWidgetLayout,
      resetWidgetLayouts,
      setAgentTasks,
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
