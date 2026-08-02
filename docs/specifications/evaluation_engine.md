# Phase C.3: Evaluation Engine Specification

The Evaluation Engine is responsible for consuming `ExecutionCompletedEvent`s from the Outbox, assessing the raw output measurements of the benchmark execution, evaluating them against criteria, and producing normalized Capability Profiles.

## 1. Evaluation Lifecycle

The Evaluation Engine operates as an event-driven pipeline separated into distinct measurement and scoring phases.

- **Pending**: An `ExecutionCompletedEvent` is picked up by the `EvaluationSubscriber`. The execution is queued for evaluation.
- **Running**: The engine retrieves the raw execution outputs and the benchmark's defined `EvaluationStrategy`. An `EvaluationStartedEvent` is emitted.
- **Evaluation (Measurement)**: Evaluators interact with outputs to extract raw facts and measurements (e.g., latency, exact_match, ROUGE).
- **Scoring**: A Scoring Engine interprets those raw facts, applies weights, normalizes them, and produces a Capability Profile.
- **Partial Success**: If evaluating a dataset of 100 prompts and 3 fail, the evaluation completes in a partial state rather than outright failing, preserving the 97 successes.
- **Completed**: Results and artifacts are persisted to the database. An `EvaluationCompletedEvent` is emitted.
- **Failed**: If the evaluator suffers a critical crash, transitions to a failed state and emits an `EvaluationFailedEvent`. The outbox retry mechanism provides fault tolerance.

## 2. Evaluation Model

- **Inputs**: 
  - `model_output_id`: The raw outputs produced during the benchmark execution.
  - `strategy_version_id`: The specific parameters and logic used to evaluate.
  - `judge_id` (Optional): If an LLM-as-a-judge is utilized.
  - **Context**: `execution_id`, `benchmark_version`, `dataset_version`, `environment`, `seed`
- **Measurement Outputs**:
  - `raw_measurements`: Unstructured JSON mapping of raw facts (e.g., {"bleu_score": 0.74, "exact_match": false, "latency_ms": 420}).
- **Scoring Outputs**:
  - `capability_profile`: The primary output vector (e.g., `Reasoning: 92`, `Python: 84`). Overall score is derived.
  - `score_explanation`: Detailed breakdown of weights and inputs (e.g., `{"overall": 84, "breakdown": {"reasoning": 90}, "weights": {"reasoning": 0.4}}`).
- **Artifacts**: 
  - First-class entities beyond JSON, supporting diverse outputs:
    - `logs.json`
    - `judge_prompt.txt`
    - `judge_response.json`
    - `screenshots/` (Vision benchmarks)
    - `traces/`

## 3. Architecture Boundary: Measurement vs Scoring

The pipeline splits into two distinct, decoupled stages:

1. **Measurement (Evaluator)**: Extracts facts from the execution. It stops at raw measurements.
2. **Scoring Engine**: Takes raw measurements, decides weights, normalizes values, evaluates pass/fail boundaries, and aggregates into a vector-based Capability Profile.

## 4. Evaluator Plugin Lifecycle

To remain extensible across text, vision, code generation, and multi-modal benchmarks, the Evaluation Engine defines a generic interface with explicit lifecycle hooks:

```python
class Evaluator:
    def prepare(self, context) -> None: ...
    def evaluate(self, execution_output) -> RawMeasurements: ...
    def postprocess(self, measurements) -> None: ...
    def cleanup(self) -> None: ...
```

### Judge Adapters (LLM Isolation)
LLM Judges are abstracted behind a `JudgeAdapter` interface (`OpenAIAdapter`, `ClaudeAdapter`, `LocalAdapter`). The Evaluator never calls vendor APIs directly, preventing vendor leak into the domain.

### Deep Reproducibility
Evaluations capture an exhaustive reproducibility matrix, versioning the:
- `Evaluator Version`
- `Dataset Version`
- `Strategy Version`
- `Prompt Version`
- `Judge Version`
- `Model Version`

## 5. Domain Events

The Evaluation Engine emits rich context to downstream consumers (Reporting/Leaderboards):

- `EvaluationStartedEvent`:
  - `evaluation_id`, `execution_id`, `strategy_version`, `timestamp`
- `EvaluationCompletedEvent`:
  - `evaluation_id`, `execution_id`, `overall_score`, `duration`, `artifact_count`, `timestamp`
- `EvaluationFailedEvent`:
  - `evaluation_id`, `execution_id`, `retryable`, `reason`, `timestamp`

## 6. Persistence Model

The persistence model (referencing `evaluation.py`) stores the decoupled stages:

- **Evaluation Records**: `EvaluationResult` stores `raw_measurements`, partial success states, and the link to `model_output_id`.
- **Score Breakdown**: `CapabilityProfile` acts as the primary output, holding a vector of `CapabilityScore`s. The `overall_score` is a derived column. It stores the `score_explanation` JSON.
- **Artifacts**: Links to external blob storage or local disk for rich media (`screenshots`, `traces`), while `EvaluationResultDetail` handles lightweight textual JSON logs.
