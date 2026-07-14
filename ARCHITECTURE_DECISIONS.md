# Architecture Decisions

## 1. Unidirectional Dependency (Execution -> Evaluation)
**Decision**: The Evaluation Service depends on the Execution Service, but not vice versa.
**Rationale**: Execution is a generic, dumb compute layer. It shouldn't care if its outputs are being evaluated by an LLM, a regex rule, or discarded. 

## 2. Evaluation State Machine Isolation
**Decision**: `EvaluationJob` tracks the lifecycle of an evaluation, independent of `AtlasRun`.
**Rationale**: An evaluation might fail and need retrying without re-running the expensive Execution step. Therefore, Evaluation needs its own `EvaluationAttempt` lifecycle.

## 3. Abstract Metric Engine
**Decision**: All pipelines must output a standardized `MetricValueModel`. The `MetricEngine` handles normalization and aggregation.
**Rationale**: By standardizing all metric outputs, the Capability Engine can operate on a uniform data structure regardless of whether the metric came from a regex rule or GPT-4.

## 4. Capability Mapping
**Decision**: The Capability Engine derives high-level "Intelligence" scores (e.g., Coding, Reasoning) directly from aggregated Metric Categories (e.g., CORRECTNESS, QUALITY).
**Rationale**: Keeps the core engine agnostic of specific benchmarks like HumanEval or MMLU. It only deals with abstract metrics.

## 5. Mock Judge Provider
**Decision**: Implemented `MockJudgeProvider` instead of a real LLM integration during the v0.6 freeze.
**Rationale**: Proves the architecture, testability, and pipeline interfaces without introducing non-deterministic failure modes or external API dependencies during the core platform build.
