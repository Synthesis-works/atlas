import { apiClient } from '@/core/api/client';
import type { AgentTask } from '../types';
import { ensureAuthenticatedSession } from '@/features/auth/services/authService';

export type AgentStatusUpdateCallback = (tasks: AgentTask[]) => void;

class AgentPollingService {
  private timerId: ReturnType<typeof setInterval> | null = null;
  private isPolling = false;
  private pollIntervalMs = 2000;
  private currentSeq = 0;
  private lastAppliedSeq: Record<string, number> = {};
  private activeTaskIds: Set<string> = new Set();
  private subscribers: Set<AgentStatusUpdateCallback> = new Set();
  private abortController: AbortController | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('visibilitychange', this.handleVisibilityChange);
    }
  }

  private handleVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      this.pause();
    } else if (this.activeTaskIds.size > 0) {
      this.resume();
      this.pollNow();
    }
  };

  public subscribe(callback: AgentStatusUpdateCallback): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  public registerActiveTasks(ids: string[]) {
    ids.forEach((id) => this.activeTaskIds.add(id));
    if (this.activeTaskIds.size > 0 && !this.isPolling) {
      this.start();
    }
  }

  public unregisterTask(id: string) {
    this.activeTaskIds.delete(id);
    if (this.activeTaskIds.size === 0) {
      this.stop();
    }
  }

  public start() {
    if (this.isPolling) return;
    this.isPolling = true;
    this.timerId = setInterval(() => this.pollNow(), this.pollIntervalMs);
    this.pollNow();
  }

  public pause() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  public resume() {
    if (this.isPolling && !this.timerId) {
      this.timerId = setInterval(() => this.pollNow(), this.pollIntervalMs);
    }
  }

  public stop() {
    this.pause();
    this.isPolling = false;
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  public async pollNow() {
    if (this.activeTaskIds.size === 0) {
      this.stop();
      return;
    }

    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();

    const seq = ++this.currentSeq;

    try {
      await ensureAuthenticatedSession();
      // Fetch status for all active tasks
      // Depending on the backend API, we might fetch them one by one or via a batch endpoint.
      // If no batch endpoint exists for agent tasks, we'll fetch them concurrently.
      const fetchPromises = Array.from(this.activeTaskIds).map(id => 
        apiClient.get<AgentTask>(`/api/v1/agent/tasks/${id}`, { signal: this.abortController!.signal })
                 .catch(() => null)
      );
      
      const results = await Promise.all(fetchPromises);
      const items = results.filter(Boolean) as AgentTask[];

      if (items.length === 0) return;

      const validUpdates: AgentTask[] = [];

      for (const item of items) {
        if (this.activeTaskIds.has(item.task_id)) {
          const lastSeq = this.lastAppliedSeq[item.task_id] || 0;
          if (seq >= lastSeq) {
            this.lastAppliedSeq[item.task_id] = seq;
            validUpdates.push(item);

            // Auto-unregister terminal states
            if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(item.status)) {
              this.activeTaskIds.delete(item.task_id);
            }
          }
        }
      }

      if (validUpdates.length > 0) {
        this.subscribers.forEach((cb) => cb(validUpdates));
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return;
    }
  }
}

export const agentPollingService = new AgentPollingService();
