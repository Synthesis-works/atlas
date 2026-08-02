# Metric Standard

The core philosophy of Atlas Evaluation is that **capabilities are benchmark-agnostic**.

## MetricValueModel
All pipelines must output metrics matching this standard representation:

```python
class MetricValueModel:
    name: str  # e.g., "pass_rate"
    value: float  # Raw value, e.g. 0.95
    category: MetricCategory  # CORRECTNESS, QUALITY, SAFETY
    direction: MetricDirection  # HIGHER_IS_BETTER
    unit: str  # percent, score
    source: str  # e.g., JudgePipeline
    aggregation: str  # mean, sum
    normalized_value: float  # 0.0 - 1.0 (added by MetricEngine)
```

## Validation & Normalization
The `MetricEngine` enforces bounds (e.g. 0 to 1, or 0 to 10) and ensures `normalized_value` is set, allowing the Capability Engine to safely aggregate diverse metrics into universal intelligence scores without knowing the underlying benchmark rules.
