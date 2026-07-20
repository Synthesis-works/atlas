# Release Notes: v0.6-evaluation-core

**Release Date:** 2026-07-14

## Overview
This release finalizes and freezes the Atlas Evaluation Core. It introduces the full end-to-end evaluation lifecycle, enabling Atlas to seamlessly ingest execution run outputs and process them through automated judging pipelines into high-level intelligence capabilities.

## Key Features & Abstractions

- **The Evaluation Controller**: A centralized finite state machine managing `EvaluationJob`s and `EvaluationAttempt`s, ensuring resilient retries and locked state transitions.
- **Pipelines**: Pluggable pipeline architectures (`ExecutionPipeline`, `RulePipeline`, `JudgePipeline`) that process raw model outputs into standardized metrics.
- **Engines**:
  - **Metric Engine**: Validates bounds, normalizes scales (e.g., 0-1), and aggregates task-level metrics into run-level metrics.
  - **Capability Engine**: Bridges the gap between raw scores and "Intelligence". It deterministically maps evaluation metrics into benchmark-agnostic capabilities (Coding, Reasoning, etc).
- **Execution Orchestration**: The `EvaluationOrchestrator` automates the translation of `RUN_COMPLETED` domain events into `EvaluationJob` lifecycles while maintaining strict unidirectional dependencies.
- **Reporting APIs**: Read-only endpoints providing transparency into capabilities, leaderboard rankings, and granular evaluation traces.

## Status
The Evaluation Architecture and Database Schema are officially **FROZEN** for v0.6.
