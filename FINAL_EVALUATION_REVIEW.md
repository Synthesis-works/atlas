# Final Evaluation Review

## Architecture Summary
The Evaluation subsystem successfully achieves separation of concerns from the Execution layer. 
- **Decoupling**: It relies solely on `RUN_COMPLETED` domain events to initiate evaluation. It queries Execution models (`AtlasRun`, `ModelOutput`) read-only and never writes back.
- **Evaluation Controller**: Owns the lifecycle of `EvaluationJob` and `EvaluationAttempt`, utilizing pessimistic locking during state transitions.
- **Pipelines**: Implemented purely as functional processors that take `PipelineContext` and output `EvaluationResultBundle`s. We have Execution, Rule, and Mocked LLM Judge pipelines.
- **Metric Engine**: Standardizes outputs, ensuring that all `MetricValue`s are validated, normalized, and aggregated uniformly before capability derivation.
- **Capability Engine**: Consumes metric sets and maps them statelessly to high-level capabilities (e.g. `CORRECTNESS` -> Coding).
- **Reporting**: Isolated to `/reports` as read-only FastAPI routers querying the persistence layer directly.

## Database Summary
- **Schema Frozen**: The schema successfully integrates composite unique constraints on versioning models (`uq_eval_pipeline_version`, `uq_judge_version`, `uq_metric_definition_version`).
- **Isolation**: Foreign keys from Evaluation to Execution are `ON DELETE CASCADE`. The reverse does not exist.

## Remaining Technical Debt
- **Pipeline Dynamic Loading**: Currently pipelines are explicitly mocked in the orchestrator. The registry needs to be tied to `EvaluationPipelineVersion` schema configurations dynamically.
- **Async Processing**: The `EvaluationOrchestrator` executes synchronously on the event thread. This needs to be moved to an async task queue (e.g., Celery) when integrating real LLM judges due to API latency.
- **Metric Mapping Overrides**: Capability mapping currently relies on hardcoded string logic in the Engine. This should be moved to the `CapabilityDefinition` configuration in the DB.

## Future Extensions
- **Composite Pipelines**: Chaining pipelines together (e.g., Execution Pipeline verifies syntax -> passes to LLM Judge Pipeline if true).
- **Real LLM Integrations**: Replacing `MockJudgeProvider` with OpenAI/Gemini/Anthropic providers.
- **Human-in-the-Loop Review**: Implementing `HumanReviewPipeline` allowing `PAUSED` evaluation states until human scores are submitted.

## Known Limitations
- The Orchestrator does not currently handle partial evaluation restarts gracefully if a pipeline fails mid-execution (it fails the whole attempt). Retries would start a new attempt from scratch.
