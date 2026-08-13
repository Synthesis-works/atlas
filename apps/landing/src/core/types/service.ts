/**
 * Core — Service Result Contract
 * Standardized async response wrapper for all domain services.
 */

export interface ServiceResult<T> {
  data: T;
  error: string | null;
}
