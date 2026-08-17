/**
 * Service — Execution Polling Manager (Milestone 3B)
 * Single-instance polling service managing batch queue status polling,
 * monotonic sequence race protection, page visibility pausing, and clean unmount teardown.
 */

import { apiClient } from '@/infrastructure/api/client';
export interface BackendExecutionResponse {
  id: string;
  status: string;
  total_items?: number;
  completed_items?: number;
}

export type StatusUpdateCallback = (executions: BackendExecutionResponse[]) => void;

class ExecutionPollingService {
  private timerId: ReturnType<typeof setInterval> | null = null;
  private isPolling = false;
  private pollIntervalMs = 3000;
  private currentSeq = 0;
  private lastAppliedSeq: Record<string, number> = {};
  private activeExecutionIds: Set<string> = new Set();
  private subscribers: Set<StatusUpdateCallback> = new Set();
  private abortController: AbortController | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('visibilitychange', this.handleVisibilityChange);
    }
  }

  private handleVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      this.pause();
    } else if (this.activeExecutionIds.size > 0) {
      this.resume();
      this.pollNow();
    }
  };

  public subscribe(callback: StatusUpdateCallback): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  public registerActiveExecutions(ids: string[]) {
    ids.forEach((id) => this.activeExecutionIds.add(id));
    if (this.activeExecutionIds.size > 0 && !this.isPolling) {
      this.start();
    }
  }

  public unregisterExecution(id: string) {
    this.activeExecutionIds.delete(id);
    if (this.activeExecutionIds.size === 0) {
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
    if (this.activeExecutionIds.size === 0) {
      this.stop();
      return;
    }

    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();

    const seq = ++this.currentSeq;

    try {
      // Query list of executions for status update
      const items = await apiClient.get<BackendExecutionResponse[]>('/api/v1/executions', {
        signal: this.abortController.signal,
      });

      if (!Array.isArray(items)) return;

      const validUpdates: BackendExecutionResponse[] = [];

      for (const item of items) {
        if (this.activeExecutionIds.has(item.id)) {
          const lastSeq = this.lastAppliedSeq[item.id] || 0;
          if (seq >= lastSeq) {
            this.lastAppliedSeq[item.id] = seq;
            validUpdates.push(item);

            // Auto-unregister terminal states
            if (['COMPLETED', 'FAILED', 'FAILED_PERMANENT', 'CANCELLED', 'TIMED_OUT'].includes(item.status)) {
              this.activeExecutionIds.delete(item.id);
            }
          }
        }
      }

      if (validUpdates.length > 0) {
        this.subscribers.forEach((cb) => cb(validUpdates));
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      // Network resilience fallback during offline / dev mode
    }
  }
}

export const executionPollingService = new ExecutionPollingService();
