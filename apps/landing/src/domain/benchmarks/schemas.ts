/**
 * Domain — Benchmarks Schemas & Validation
 * Pure validation helpers for Benchmark models.
 */

import type { Benchmark } from './types';

export function validateBenchmark(data: Partial<Benchmark>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!data.name || data.name.trim().length === 0) {
    errors.push('Benchmark name is required.');
  }
  if (!data.category) {
    errors.push('Benchmark category is required.');
  }
  if (!data.version || !/^\d+\.\d+\.\d+$/.test(data.version)) {
    errors.push('Version must follow semver format (e.g. 1.0.0).');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
