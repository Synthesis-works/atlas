# Benchmarks Feature Module

## Purpose
Self-contained functional business domain for managing AI benchmark registries, active execution queues, live log monitors, analytics, and side-by-side specification comparisons.

## Public API
- `BenchmarksFeature`: Main entry point React component.
- `useBenchmarks()`: Custom selector hook for benchmarking state.

## Folder Structure
- `/components`: Visual components (Header, KPIs, Registry, Drawer, Queue, Monitor).
- `/config`: Declarative filters, columns, and chart configurations.
- `/hooks`: Custom feature selectors.
- `/services`: Functional async domain service calls (`benchmarkService.ts`).
- `/lib`: Helper search parsers, mock log generators, and formatters.
