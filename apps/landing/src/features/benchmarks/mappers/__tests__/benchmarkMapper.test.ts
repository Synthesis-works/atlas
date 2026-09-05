/**
 * Regression tests for Finding 5.
 * The benchmark mapper/adapter must never invent a verification score when the
 * backend returns no telemetry: null stays null and surfaces as '—' in the UI.
 */

import { describe, expect, it } from 'vitest';
import { BenchmarkMapper } from '../benchmarkMapper';
import { normalizeBenchmarkPayload } from '../../../../domain/benchmarks/adapters';

describe('BenchmarkMapper.toDomain verification score honesty', () => {
  it('returns null when no score telemetry exists', () => {
    const mapped = BenchmarkMapper.toDomain({
      id: 'bm-1',
      name: 'No Runs Yet',
      average_score: null,
      latest_score: null,
    });
    expect(mapped.verificationScore).toBeNull();
  });

  it('normalizes a canonical 0-1 score to a 0-100 percentage', () => {
    const mapped = BenchmarkMapper.toDomain({
      id: 'bm-2',
      name: 'Scored',
      average_score: 0.72,
      latest_score: 0.912,
    });
    expect(mapped.verificationScore).toBe(91);
  });

  it('preserves legacy 0-100 telemetry without inflating it', () => {
    const mapped = BenchmarkMapper.toDomain({
      id: 'bm-2b',
      name: 'Legacy Scored',
      average_score: null,
      latest_score: 91.2,
    });
    expect(mapped.verificationScore).toBe(91);
  });

  it('falls back to the average score when latest is absent', () => {
    const mapped = BenchmarkMapper.toDomain({
      id: 'bm-3',
      name: 'Average Only',
      average_score: 0.4,
      latest_score: null,
    });
    expect(mapped.verificationScore).toBe(40);
  });

  it('does not turn a falsy numeric zero into a null score', () => {
    const mapped = BenchmarkMapper.toDomain({
      id: 'bm-4',
      name: 'Zero Score',
      average_score: null,
      latest_score: 0,
    });
    expect(mapped.verificationScore).toBe(0);
  });
});

describe('normalizeBenchmarkPayload verification score honesty', () => {
  it('returns null when the raw payload omits the score', () => {
    expect(normalizeBenchmarkPayload({ id: 'bm-5', name: 'Empty' }).verificationScore).toBeNull();
  });

  it('never defaults a missing score to 100', () => {
    const normalized = normalizeBenchmarkPayload({ id: 'bm-6', name: 'Empty' });
    expect(normalized.verificationScore).not.toBe(100);
  });

  it('preserves an explicit score', () => {
    expect(normalizeBenchmarkPayload({ id: 'bm-7', name: 'Scored', verificationScore: 88 }).verificationScore).toBe(88);
  });
});