"""Client-side agent evaluation-parity tools (v3.4).

Each tool validates its arguments, delegates to a corresponding ``AtlasClient``
method, and returns a compact :class:`ToolResult`.

Confirmation model:
    * READ tools (``get_evaluation_results`` / ``compare_results`` /
      ``list_report_runs``) never confirm.
    * WRITE tools (``evaluate_run`` / ``create_evaluation_cases`` /
      ``generate_report``) are gated by the standard REPL confirmation
      (``required_permission = WRITE``).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from cli.agent.tools.base import AgentPermission, BaseTool, ToolResult
from cli.agent.tools.library import _ok, _parse


class _ProjectArgs(BaseModel):
    project_id: str


class _ExecutionArgs(BaseModel):
    project_id: str
    execution_id: str


class _DatasetArgs(BaseModel):
    project_id: str
    dataset_id: str


class _CaseItem(BaseModel):
    task_id: str
    test_case_id: str | None = None
    expected_answer: str | None = None
    evaluation_method: str | None = None
    accepted_answers: list[str] = Field(default_factory=list)
    rubric_criteria: dict[str, Any] | None = None


class _EvaluationCasesArgs(BaseModel):
    project_id: str
    dataset_id: str
    evaluation_cases: list[_CaseItem]


class _CompareArgs(BaseModel):
    project_id: str
    execution_ids: list[str] = Field(min_length=1)


class _ReportArgs(BaseModel):
    project_id: str
    title: str = Field(..., max_length=255)
    benchmark_id: str | None = None
    execution_id: str | None = None
    version_string: str | None = None


def _case_to_payload(item: _CaseItem) -> dict[str, Any]:
    payload: dict[str, Any] = {"task_id": item.task_id}
    if item.test_case_id is not None:
        payload["test_case_id"] = item.test_case_id
    if item.expected_answer is not None:
        payload["expected_answer"] = item.expected_answer
    if item.evaluation_method is not None:
        payload["evaluation_method"] = item.evaluation_method
    if item.accepted_answers:
        payload["accepted_answers"] = item.accepted_answers
    if item.rubric_criteria is not None:
        payload["rubric_criteria"] = item.rubric_criteria
    return payload


def _cli_case_to_sdk(item: _CaseItem) -> Any:
    from atlas_sdk.models.evaluation import EvaluationCaseItem

    return EvaluationCaseItem(**_case_to_payload(item))


# ── reading (READ) ────────────────────────────────────────────────────────


class GetEvaluationResultsTool(BaseTool):
    name = "get_evaluation_results"
    description = (
        "Read the evaluation results for an execution (by its id and project_id). "
        "Returns the overall score, evaluated/passed counts, and per-output "
        "results. Use after evaluate_run to check the outcome."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "execution_id": {"type": "string", "description": "Execution UUID."},
        },
        "required": ["project_id", "execution_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ExecutionArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        results = client.get_evaluation_results(parsed.project_id, parsed.execution_id)
        per_case = [
            {
                "model_output_id": str(r.model_output_id),
                "passed": r.passed,
                "status": r.status,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
            }
            for r in results.results
        ]
        return _ok(
            f"Execution {parsed.execution_id}: {results.passed_outputs}/{results.evaluated_outputs}"
            f" passed (overall {results.overall_score})",
            {
                "execution_id": str(results.execution_id),
                "status": results.status,
                "overall_score": results.overall_score,
                "profile_id": str(results.profile_id) if results.profile_id else None,
                "total_outputs": results.total_outputs,
                "evaluated_outputs": results.evaluated_outputs,
                "passed_outputs": results.passed_outputs,
                "results": per_case,
            },
        )


class CompareResultsTool(BaseTool):
    name = "compare_results"
    description = (
        "Rank a set of executions by overall evaluation score (read-only). Takes "
        "a project_id and a list of execution_ids; returns a best-first "
        "leaderboard with per-execution rank, target model, and pass counts."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "execution_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Execution UUIDs to compare.",
            },
        },
        "required": ["project_id", "execution_ids"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_CompareArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        resp = client.compare_executions(parsed.project_id, parsed.execution_ids)
        rows = [
            {
                "rank": row.rank,
                "execution_id": str(row.execution_id),
                "target_model": row.target_model,
                "overall_score": row.overall_score,
                "passed_outputs": row.passed_outputs,
                "total_outputs": row.total_outputs,
            }
            for row in resp.leaderboard
        ]
        summary = "; ".join(
            f"#{row['rank']} {row['target_model']} {row['overall_score']}" for row in rows
        )
        return _ok(f"Comparison: {summary}", {"leaderboard": rows})


class ListReportRunsTool(BaseTool):
    name = "list_report_runs"
    description = (
        "List persisted reports for a project (by its id). Returns report ids, "
        "names, and their versions/metrics."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
        },
        "required": ["project_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ProjectArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        data = client.list_reports(parsed.project_id)
        items = [
            {
                "id": str(report.id),
                "name": report.name,
                "version_count": len(report.versions),
                "versions": [
                    {
                        "id": str(v.id),
                        "version_string": v.version_string,
                        "summary": v.summary,
                        "metrics": [
                            {"metric_name": m.metric_name, "metric_value": m.metric_value}
                            for m in v.metrics
                        ],
                    }
                    for v in report.versions
                ],
            }
            for report in data.reports
        ]
        summary = "; ".join(f"{it['name']} ({it['id']})" for it in items[:15])
        return _ok(
            f"{data.total} report(s): {summary}",
            {"reports": items, "total": data.total},
        )


# ── authoring (WRITE) ─────────────────────────────────────────────────────


class EvaluateRunTool(BaseTool):
    name = "evaluate_run"
    description = (
        "Enqueue a background evaluation for a completed execution. MUTATING: "
        "requires confirmation. Takes a project_id and execution_id. The run is "
        "evaluated asynchronously; poll get_evaluation_results to read the "
        "outcome."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "execution_id": {"type": "string", "description": "Execution UUID."},
        },
        "required": ["project_id", "execution_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ExecutionArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        enqueued = client.enqueue_evaluation(parsed.project_id, parsed.execution_id)
        return _ok(
            f"Evaluation enqueued for execution {parsed.execution_id} "
            f"({enqueued.message}). Poll get_evaluation_results to read the outcome.",
            {
                "execution_id": str(enqueued.execution_id),
                "status": enqueued.status,
            },
        )


class CreateEvaluationCasesTool(BaseTool):
    name = "create_evaluation_cases"
    description = (
        "Attach evaluation-case metadata (expected_answer, evaluation_method, "
        "accepted_answers, rubric_criteria) to tasks/test cases in a dataset. "
        "MUTATING: requires confirmation. Takes a project_id, dataset_id, and a "
        "list of evaluation_cases (each {task_id, optional test_case_id, "
        "expected_answer, evaluation_method})."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "dataset_id": {"type": "string", "description": "Dataset UUID."},
            "evaluation_cases": {
                "type": "array",
                "items": {"type": "object"},
                "description": (
                    "Each {task_id, optional test_case_id, expected_answer, "
                    "evaluation_method, accepted_answers, rubric_criteria}."
                ),
            },
        },
        "required": ["project_id", "dataset_id", "evaluation_cases"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_EvaluationCasesArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        result = client.create_evaluation_cases(
            parsed.project_id,
            parsed.dataset_id,
            [_cli_case_to_sdk(c) for c in parsed.evaluation_cases],
        )
        return _ok(
            f"Evaluation cases: {len(result.written)} written, {result.skipped} skipped "
            f"in dataset {parsed.dataset_id}",
            {
                "dataset_id": str(result.dataset_id),
                "written": [
                    {
                        "test_case_id": str(w.test_case_id),
                        "task_id": str(w.task_id),
                        "evaluation_method": w.evaluation_method,
                        "expected_answer": w.expected_answer,
                    }
                    for w in result.written
                ],
                "skipped": result.skipped,
            },
        )


class GenerateReportTool(BaseTool):
    name = "generate_report"
    description = (
        "Create a persisted report for a project, optionally populated with an "
        "execution's evaluation metrics. MUTATING: requires confirmation. Takes "
        "a project_id, a title, and optional execution_id / benchmark_id / "
        "version_string."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "title": {"type": "string", "description": "Report title."},
            "benchmark_id": {"type": "string", "description": "Optional benchmark UUID."},
            "execution_id": {
                "type": "string",
                "description": "Optional execution UUID whose metrics populate the report.",
            },
            "version_string": {"type": "string", "description": "Optional report version."},
        },
        "required": ["project_id", "title"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ReportArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        report = client.generate_report(
            parsed.project_id,
            parsed.title,
            benchmark_id=parsed.benchmark_id,
            execution_id=parsed.execution_id,
            version_string=parsed.version_string,
        )
        return _ok(
            f"Created report {report.name} ({report.id}) in project {parsed.project_id} "
            f"[{len(report.versions)} version(s)]",
            {"report_id": str(report.id), "name": report.name},
        )
