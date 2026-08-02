# Leaderboard Contract

This document serves as the canonical specification for all leaderboard features and APIs within the Atlas backend. Future implementation of leaderboards, aggregation pipelines, and ranking APIs must adhere to these rules.

## 1. Leaderboard Types

The platform supports four distinct types of leaderboards:

1. **Benchmark Leaderboard**: Ranks models based on their performance on a specific benchmark version (e.g., *HumanEval v2*).
2. **Capability Leaderboard**: Aggregates performance across multiple benchmarks mapped to a specific capability (e.g., *Coding*, *Reasoning*).
3. **Global Leaderboard**: A weighted average ranking of models across all capabilities and benchmarks on the platform.
4. **Organization Leaderboard** *(Future)*: Ranks models evaluated strictly within the boundaries of a single organization's private datasets and benchmarks.

## 2. Capability Aggregation Rules

When aggregating performance across a capability (e.g., Coding, Reasoning), the following mathematical contract applies:

- **Aggregation Method**: Simple unweighted average of the underlying benchmark scores.
- **Missing Benchmarks**: Benchmarks without successful executions for a given model are ignored (they do not penalize the model as zeroes).
- **Benchmark Versioning**: The aggregation takes the latest execution per distinct *benchmark version*. If a model is evaluated on multiple versions of the same benchmark (e.g., MMLU v1 and MMLU v2), both contribute to the capability average.

## 3. Eligibility Rules

A result is only eligible for leaderboard ranking if it meets all the following criteria:

- The execution `status` is `COMPLETED`.
- The evaluation `status` is `SUCCESS`.
- *(If applicable)* The execution visibility is `PUBLIC`.
- Failed, cancelled, or running executions **must never** appear in leaderboard aggregates.

## 3. Freshness Window

Leaderboards **do not** use historical best scores. 

Ranking is determined by the **latest successful execution** per model. Specifically, the uniqueness constraint for any single leaderboard entry is:
`(benchmark_version, target_model)`

This ensures the leaderboard is deterministic, reproducible, and fair. It prevents gaming the system through repeated execution farming to capture statistical outliers.

## 4. Score Normalization

The Leaderboard subsystem **does not** perform metric normalization. 

It consumes the canonical `overall_score` produced by the Reporting Engine. Any necessary metric normalization (e.g., mapping F1, BLEU, or custom pass rates to a comparable 0-100 scale) is strictly the responsibility of the Evaluation and Reporting layers. 

The leaderboard's sole responsibilities are: **Sort, Rank, Paginate, and Filter**.

## 5. Tie-Breaking Hierarchy

In the event of identical scores, tie-breaking must follow this strict, deterministic hierarchy. We do not use execution cost or timestamps as tie-breakers because earlier or cheaper does not necessarily mean better.

1. **Primary**: `overall_score DESC`
2. **Secondary**: `capability_score DESC` *(if available for capability leaderboards)*
3. **Tertiary**: `completed_at DESC` *(favors the most recently verified capability capability/benchmark execution)*
4. **Final (Deterministic Fallback)**: `execution_id ASC` *(guarantees a stable sort order across pagination)*

## 6. Versioning

**Every leaderboard is scoped to exactly one benchmark version** unless explicitly documented as an aggregated capability or global leaderboard. 
For example, *MMLU v1* and *MMLU v2* are distinct leaderboards. The leaderboard subsystem must never silently merge scores across different benchmark versions.

## 7. Caching Expectations

Leaderboards are inherently read-heavy. 
Implementations are expected to utilize techniques such as:
- Materialized Views
- Cached Snapshots
- Redis Caching

**Leaderboard requests must not compute large aggregations synchronously on the fly.**
