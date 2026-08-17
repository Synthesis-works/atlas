import { apiClient, getApiBaseUrl, getAuthToken, setAuthToken } from './apiClient';
import type { AgentTask, AgentProviderOption, AgentReport } from '../types';

/**
 * Build the download filename as `<report-name>-v<version>.<ext>` from sanitized real data.
 * Falls back to the execution id when no report name is available.
 */
export function buildExportFilename(
  format: 'json' | 'csv',
  reportName?: string,
  versionString?: string,
): string {
  const base =
    (reportName || '')
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '') || 'report';
  const version = versionString ? `-v${versionString.replace(/^v/i, '')}` : '';
  return `${base}${version}.${format}`;
}

export async function fetchAgentReport(reportId: string): Promise<{ data: AgentReport | null; error: any }> {
  try {
    const response = await apiClient.get<AgentReport>(`/api/v1/agent/reports/${reportId}`);
    return { data: response, error: null };
  } catch (error) {
    console.error(`Failed to fetch agent report ${reportId}:`, error);
    return { data: null, error };
  }
}

/**
 * Download a real run report artifact from the reporting service export endpoint.
 * The endpoint requires the report:read permission (authenticated user with a valid JWT).
 * Returns a structured error so callers can surface 401/403/404/500 messages.
 */
export async function downloadExecutionReport(
  executionId: string,
  format: 'json' | 'csv' = 'json',
): Promise<{ data: Blob | null; error: { status?: number; message: string } | null }> {
  try {
    const token = getAuthToken();
    const response = await fetch(
      `${getApiBaseUrl()}/api/v1/reports/runs/${executionId}/export?format=${format}`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          Authorization: `Bearer ${token ?? ''}`,
        },
      },
    );
    if (!response.ok) {
      if (response.status === 401) setAuthToken(null);
      let message = `Export request failed with status ${response.status}.`;
      if (response.status === 401) {
        message = 'Your session has expired. Please sign in again and retry the download.';
      } else if (response.status === 403) {
        message = 'You do not have permission to download this report.';
      } else if (response.status === 404) {
        message = 'This report is no longer available.';
      } else if (response.status >= 500) {
        message = 'The server could not generate the report. Please try again.';
      }
      return { data: null, error: { status: response.status, message } };
    }
    const blob = await response.blob();
    return { data: blob, error: null };
  } catch (error: any) {
    console.error(`Failed to download execution report ${executionId}:`, error);
    return {
      data: null,
      error: { status: 0, message: error?.message || 'Network error while downloading the report.' },
    };
  }
}

export async function fetchAgentProviders(): Promise<{ data: AgentProviderOption[] | null; error: any }> {
  try {
    const response = await apiClient.get<AgentProviderOption[]>('/api/v1/agent/providers');
    return { data: response, error: null };
  } catch (error) {
    console.error('Failed to fetch agent providers:', error);
    return { data: null, error };
  }
}

export async function fetchAgentTasks(): Promise<{ data: AgentTask[] | null; error: any }> {
  try {
    const response = await apiClient.get<AgentTask[]>('/api/v1/agent/tasks');
    return { data: response, error: null };
  } catch (error) {
    console.error('Failed to fetch agent tasks:', error);
    return { data: null, error };
  }
}

export async function fetchAgentTask(taskId: string): Promise<{ data: AgentTask | null; error: any }> {
  try {
    const response = await apiClient.get<AgentTask>(`/api/v1/agent/tasks/${taskId}`);
    return { data: response, error: null };
  } catch (error) {
    console.error(`Failed to fetch agent task ${taskId}:`, error);
    return { data: null, error };
  }
}

/**
 * Submit a new agent task.
 */
export async function submitAgentTask(
  goal: string,
  provider: string,
  model?: string,
): Promise<{ data: AgentTask | null; error: any }> {
  try {
    const payload: Record<string, any> = { goal, provider };
    if (model) {
      payload.model = model;
    }
    const response = await apiClient.post<AgentTask>('/api/v1/agent/tasks', payload);
    return { data: response, error: null };
  } catch (error) {
    console.error('Failed to submit agent task:', error);
    return { data: null, error };
  }
}


/**
 * Submit a clarification answer to a waiting task.
 * Backend expects: { clarification_id?, answer?, response? }
 */
export async function sendAgentClarification(
  taskId: string,
  responseText: string,
  clarificationId?: string,
): Promise<{ data: any; error: any }> {
  try {
    const response = await apiClient.post(`/api/v1/agent/tasks/${taskId}/clarify`, {
      response: responseText,
      clarification_id: clarificationId,
    });
    return { data: response, error: null };
  } catch (error) {
    console.error(`Failed to send clarification for ${taskId}:`, error);
    return { data: null, error };
  }
}

/**
 * Approve a pending tool action.
 * Backend expects: { approval_token: string }
 * The approval_token is included in the task payload when status === WAITING_FOR_APPROVAL.
 */
export async function approveAgentAction(
  taskId: string,
  approvalToken: string,
): Promise<{ data: any; error: any }> {
  try {
    const response = await apiClient.post(`/api/v1/agent/tasks/${taskId}/approve`, {
      approval_token: approvalToken,
    });
    return { data: response, error: null };
  } catch (error) {
    console.error(`Failed to approve action for ${taskId}:`, error);
    return { data: null, error };
  }
}

/**
 * Run an agent task again (creates a new task cloning the old one's parameters).
 * Backend returns the new task's task_id.
 */
export async function runAgentTaskAgain(taskId: string): Promise<{ data: any; error: any }> {
  try {
    const response = await apiClient.post(`/api/v1/agent/tasks/${taskId}/run-again`);
    return { data: response, error: null };
  } catch (error) {
    console.error(`Failed to run agent task again ${taskId}:`, error);
    return { data: null, error };
  }
}

/**
 * Cancel a running task.
 */
export async function cancelAgentTask(taskId: string): Promise<{ data: any; error: any }> {
  try {
    const response = await apiClient.post(`/api/v1/agent/tasks/${taskId}/cancel`);
    return { data: response, error: null };
  } catch (error) {
    console.error(`Failed to cancel agent task ${taskId}:`, error);
    return { data: null, error };
  }
}


