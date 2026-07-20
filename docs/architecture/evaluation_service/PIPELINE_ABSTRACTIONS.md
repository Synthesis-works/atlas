# Pipeline Abstractions

The Pipeline framework is designed as a functional transformation step. 

## Base Classes

1. **`EvaluationPipeline`**: The base class for all pipelines. Requires implementing `evaluate(context) -> EvaluationResultBundle`.
2. **`PipelineContext`**: A standardized object containing Execution outputs, benchmark definitions, and configurations.
3. **`EvaluationResultBundle`**: The container for outputs (Metrics, Artifacts, JudgeTraces) passed to the Metric Engine and Controller for persistence.

## Implementations
- **`RulePipeline`**: Evaluates outputs based on Regex or static rules.
- **`ExecutionPipeline`**: Evaluates code execution outputs (Pass/Fail) based on assertion testing results.
- **`JudgePipeline`**: Defers evaluation to a `JudgeProvider` (e.g. LLM), passing the prompt and rubric to retrieve a score and reasoning trace.
