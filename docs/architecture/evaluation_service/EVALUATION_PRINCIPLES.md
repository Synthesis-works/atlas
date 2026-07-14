# Evaluation Service Principles

The Evaluation Service acts as the reasoning engine for Atlas. Its primary question is: **"How good was the result?"**

To maintain a healthy, scalable architecture, all design decisions within the Evaluation Service must strictly adhere to the following principles:

## 1. Execution is a Black Box Dependency
The Evaluation Service strictly consumes the Execution API contract and emitted events. It has zero knowledge of orchestration, scheduling, worker node health, or recovery mechanisms.
* **Rule**: Evaluation never mutates the state of an `AtlasRun` or `AtlasTask`.
* **Rule**: Execution has zero dependency on Evaluation (unidirectional dependency).

## 2. Judges are Replaceable Interfaces
The architecture must never hardcode specific evaluation mechanisms (e.g., "LLM Judge" or "Regex Judge").
* **Rule**: All scoring mechanisms must implement a generic `Judge` interface.
* **Rule**: Rule-based judges, LLM-based judges, human judges, and hybrid judges are treated identically by the controller.

## 3. Metrics are Standardized and Immutable
Evaluation produces numerous metrics (e.g., Accuracy, Pass@k, Latency, Cost). They must all conform to a unified abstraction.
* **Rule**: Every metric is stored as a standard `MetricValue` (name, value, unit, confidence, metadata).
* **Rule**: Once an evaluation is complete, its calculated metrics are immutable.

## 4. Capability Scores are Derived
We do not manually score higher-order capabilities like "Reasoning", "Coding", or "Safety".
* **Rule**: The Capability Engine derives capability profiles purely by consuming and aggregating raw `EvaluationResults`.

## 5. Reporting is Read-Only
The Reporting Service will eventually consume these metrics and capability profiles.
* **Rule**: Evaluation focuses purely on computation and storage of metrics, leaving presentation, dashboards, and filtering strictly to the Reporting layer.
