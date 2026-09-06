"""Client-side agent tool library (Phase 2) — one tool per Atlas capability.

Every tool validates its arguments, delegates to an existing ``AtlasClient``
method, and returns a compact :class:`ToolResult`.  None of these tools grant
arbitrary code execution, shell, filesystem, or generic HTTP access — they are
the only surface the agent loop can act on.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from cli.agent.tools.base import AgentPermission, BaseTool, ToolResult

# ── argument-validation models ─────────────────────────────────────────────

_POLL_INTERVAL = 2


class _LimitArgs(BaseModel):
    limit: int = Field(50, ge=1, le=100)


class _BenchmarkIdArgs(BaseModel):
    benchmark_id: str


class _SubmitRunArgs(BaseModel):
    benchmark_version_id: str
    target_model: str
    dataset_version_id: str | None = None


class _RunIdArgs(BaseModel):
    execution_id: str


class _WatchArgs(BaseModel):
    execution_id: str
    max_polls: int = Field(_POLL_INTERVAL, ge=1, le=40)
    interval: float = Field(2.0, gt=0, le=30.0)


class _ReportIdArgs(BaseModel):
    run_id: str


class _ExportArgs(BaseModel):
    run_id: str
    format: str = Field("json", pattern="^(json|csv)$")
    include_prompt: bool = False
    include_expected_output: bool = False


class _LeaderboardArgs(BaseModel):
    benchmark_version_id: str
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class _SearchArgs(BaseModel):
    project_id: str
    q: str
    entity_types: list[str] = Field(default_factory=list)
    limit: int = Field(20, ge=1, le=100)


class _ModelNameArgs(BaseModel):
    model_name: str


class _ActivityArgs(BaseModel):
    activity_type: str = Field("all", pattern="^(all|benchmarks|executions|models)$")
    limit: int = Field(10, ge=1, le=50)


def _parse(model: type[BaseModel], arguments: dict[str, Any]) -> Any:
    try:
        return model.model_validate(arguments)
    except ValidationError as exc:
        return exc


def _ok(summary: str, data: dict[str, Any] | None = None) -> ToolResult:
    return ToolResult(ok=True, summary=summary, data=data)


# ── tools ──────────────────────────────────────────────────────────────────


class ListBenchmarksTool(BaseTool):
    name = "list_benchmarks"
    description = (
        "List published benchmarks. Returns benchmark ids and names that the "
        "agent can pass to get_benchmark_versions or interpret."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max entries (1-100).",
                "default": 50,
            }
        },
        "required": [],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_LimitArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        page = client.list_benchmarks(limit=parsed.limit)
        items = [{"id": str(b.id), "name": b.name, "state": b.state} for b in page.items]
        summary = " ".join(
            f"{i + 1}. {it['name']} ({it['id']}) [{it['state']}]" for i, it in enumerate(items[:15])
        )
        return _ok(
            f"{len(items)} benchmark(s): {summary}",
            {"items": items, "total": page.total},
        )


class GetBenchmarkVersionsTool(BaseTool):
    name = "get_benchmark_versions"
    description = (
        "List version ids and version strings for a benchmark (by its id from "
        "list_benchmarks). A benchmark_version_id is needed to submit a run."
    )
    parameters_schema = {
        "type": "object",
        "properties": {"benchmark_id": {"type": "string", "description": "Benchmark UUID."}},
        "required": ["benchmark_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_BenchmarkIdArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        versions = client.list_benchmark_versions(parsed.benchmark_id)
        items = [
            {"version_id": str(v.id), "version_string": v.version_string, "state": v.state}
            for v in versions
        ]
        summary = " ".join(
            f"{v['version_string']} ({v['version_id']}) [{v['state']}]" for v in items[:15]
        )
        return _ok(
            f"{len(items)} version(s): {summary}",
            {"items": items, "total": len(items)},
        )


class ListModelsTool(BaseTool):
    name = "list_models"
    description = (
        "List execution target models accepted by submit_run's target_model "
        "(e.g. 'mock' or 'provider/model')."
    )
    parameters_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        models = client.list_models()
        items = [
            {
                "id": m.id,
                "provider": m.provider,
                "status": m.status.value if hasattr(m.status, "value") else str(m.status),
            }
            for m in models
        ]
        ids = ", ".join(it["id"] for it in items[:20])
        return _ok(f"Available models: {ids}", {"models": items, "total": len(items)})


class SearchTool(BaseTool):
    name = "search"
    description = (
        "Free-text search within a project across benchmarks and executions "
        "(e.g. find benchmarks related to 'counting', or executions for a "
        "model). Takes a project_id, a query string, and an optional "
        "entity_types list (benchmark|execution). Results are scoped to the "
        "given project only."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "q": {"type": "string", "description": "Search query string."},
            "entity_types": {
                "type": "array",
                "items": {"type": "string", "enum": ["benchmark", "execution"]},
                "description": "Optional entity types to restrict the search to.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (1-100).",
                "default": 20,
            },
        },
        "required": ["project_id", "q"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_SearchArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        page = client.search(
            parsed.project_id,
            parsed.q,
            entity_types=parsed.entity_types or None,
            limit=parsed.limit,
        )
        items = [
            {
                "id": str(r.id),
                "entity_type": r.entity_type,
                "title": r.title,
                "subtitle": r.subtitle,
                "score": r.score,
            }
            for r in page.items
        ]
        summary = "; ".join(
            f"[{it['entity_type']}] {it['title']} ({it['id']})" for it in items[:15]
        )
        return _ok(
            f"{len(items)} result(s) for '{parsed.q}' in project {parsed.project_id}: {summary}",
            {"items": items, "total": page.total},
        )


class SubmitRunTool(BaseTool):
    name = "submit_run"
    description = (
        "Submit a new execution (run) for a benchmark version with a target model. "
        "MUTATING: creates a run. Returns the queued execution with its id."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_version_id": {"type": "string", "description": "Benchmark version UUID."},
            "target_model": {"type": "string", "description": "Target model id (e.g. mock)."},
            "dataset_version_id": {
                "type": "string",
                "description": "Optional dataset version UUID.",
            },
        },
        "required": ["benchmark_version_id", "target_model"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_SubmitRunArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        execution = client.submit_execution(
            parsed.benchmark_version_id,
            target_model=parsed.target_model,
            dataset_version_id=parsed.dataset_version_id,
        )
        return _ok(
            f"Submitted run {execution.id} for version {parsed.benchmark_version_id} "
            f"({execution.target_model}); status {execution.status}",
            {"execution_id": str(execution.id), "status": execution.status},
        )


class GetRunTool(BaseTool):
    name = "get_run"
    description = "Fetch details (id, status, progress, target model) for an execution/run."
    parameters_schema = {
        "type": "object",
        "properties": {"execution_id": {"type": "string", "description": "Execution UUID."}},
        "required": ["execution_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_RunIdArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        execution = client.get_execution(parsed.execution_id)
        progress = f"{execution.completed_items}/{execution.total_items}"
        return _ok(
            f"Run {execution.id}: status {execution.status}, model "
            f"{execution.target_model}, progress {progress}",
            {
                "execution_id": str(execution.id),
                "status": execution.status,
                "target_model": execution.target_model,
                "progress": progress,
            },
        )


class WatchRunTool(BaseTool):
    name = "watch_run"
    description = (
        "Poll an execution until it reaches a terminal state (COMPLETED, FAILED, "
        "CANCELLED, TIMED_OUT) or the poll bound is hit. Bounded — never blocks "
        "indefinitely."
    )
    _TERMINAL = frozenset({"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"})
    parameters_schema = {
        "type": "object",
        "properties": {
            "execution_id": {"type": "string", "description": "Execution UUID."},
            "max_polls": {"type": "integer", "description": "Max polls (1-40).", "default": 2},
        },
        "required": ["execution_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_WatchArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        last = None
        for _ in range(parsed.max_polls):
            execution = client.get_execution(parsed.execution_id)
            last = execution
            if execution.status in self._TERMINAL:
                return _ok(
                    f"Run {execution.id} reached terminal state {execution.status} "
                    f"({execution.completed_items}/{execution.total_items})",
                    {"execution_id": str(execution.id), "status": execution.status},
                )
            time.sleep(parsed.interval)
        if last is not None:
            return _ok(
                f"Run {last.id} still {last.status} after {parsed.max_polls} polls "
                f"({last.completed_items}/{last.total_items})",
                {"execution_id": str(last.id), "status": last.status},
            )
        return ToolResult(ok=False, summary="no state observed", error="watch failed")


class GetReportTool(BaseTool):
    name = "get_report"
    description = "Fetch the detailed report summary (score breakdown) for a run."
    parameters_schema = {
        "type": "object",
        "properties": {"run_id": {"type": "string", "description": "Run UUID."}},
        "required": ["run_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ReportIdArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        summary = client.get_report_run(parsed.run_id)
        score = f"{summary.overall_score:.1f}" if summary.overall_score is not None else "n/a"
        breakdown = {c.capability_name: round(c.score, 2) for c in summary.scores}
        return _ok(
            f"Run {summary.run_id}: status {summary.evaluation_status}, overall score "
            f"{score}; {len(summary.scores)} capability score(s)",
            {
                "run_id": str(summary.run_id),
                "evaluation_status": summary.evaluation_status,
                "overall_score": summary.overall_score,
                "scores": breakdown,
            },
        )


class ExportReportTool(BaseTool):
    name = "export_report"
    description = (
        "Export a report to a file written by the CLI (json or csv). MUTATING: "
        "writes a file to disk."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "description": "Run UUID."},
            "format": {"type": "string", "description": "json or csv.", "default": "json"},
            "include_prompt": {"type": "boolean", "description": "Include prompts."},
            "include_expected_output": {
                "type": "boolean",
                "description": "Include expected outputs.",
            },
        },
        "required": ["run_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ExportArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        result = client.export_report_run(
            parsed.run_id,
            format_type=parsed.format,
            include_prompt=parsed.include_prompt,
            include_expected_output=parsed.include_expected_output,
        )
        return _ok(
            f"Exported report to {result.filename} ({len(result.content)} bytes, {result.format})",
            {
                "filename": result.filename,
                "bytes": len(result.content),
                "run_id": parsed.run_id,
                "format": parsed.format,
            },
        )


class GetLeaderboardTool(BaseTool):
    name = "get_leaderboard"
    description = "Fetch the ranked leaderboard for a benchmark version."
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_version_id": {"type": "string", "description": "Benchmark version UUID."},
            "limit": {"type": "integer", "description": "Max entries (1-100).", "default": 20},
            "offset": {"type": "integer", "description": "Offset.", "default": 0},
        },
        "required": ["benchmark_version_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_LeaderboardArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        board = client.get_benchmark_leaderboard(
            parsed.benchmark_version_id, limit=parsed.limit, offset=parsed.offset
        )
        rows = [
            {
                "rank": e.rank,
                "model": e.model_name,
                "score": e.overall_score,
                "benchmarks": e.benchmark_count,
            }
            for e in board.entries.items
        ]
        summary = "; ".join(f"#{r['rank']} {r['model']} {r['score']:.2f}" for r in rows[:15])
        return _ok(
            f"{len(rows)} leaderboard entries for {board.title}: {summary}",
            {"rows": rows, "total": board.entries.total},
        )


class GetModelSummaryTool(BaseTool):
    name = "get_model_summary"
    description = "Fetch the aggregate performance summary for a model (score, rank, benchmarks)."
    parameters_schema = {
        "type": "object",
        "properties": {"model_name": {"type": "string", "description": "Model id (e.g. mock)."}},
        "required": ["model_name"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ModelNameArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        summary = client.get_model_summary(parsed.model_name)
        avg = f"{summary.average_score:.2f}" if summary.average_score is not None else "n/a"
        return _ok(
            f"Model {summary.model}: {summary.benchmarks} benchmark(s), average score {avg}",
            {
                "model": summary.model,
                "benchmarks": summary.benchmarks,
                "average_score": summary.average_score,
            },
        )


class GetActivityTool(BaseTool):
    name = "get_activity"
    description = (
        "Show recent platform activity. activity_type is one of all|benchmarks|executions|models."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "activity_type": {
                "type": "string",
                "description": "all|benchmarks|executions|models.",
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "Max entries per section (1-50).",
                "default": 10,
            },
        },
        "required": [],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_ActivityArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        sections: dict[str, Any] = {}
        if parsed.activity_type in ("all", "benchmarks"):
            sections["benchmarks"] = [
                b.name for b in client.get_recent_benchmarks(limit=parsed.limit)
            ]
        if parsed.activity_type in ("all", "executions"):
            sections["executions"] = [
                f"{e.target_model} on {e.benchmark_name} "
                f"[{e.status.value if hasattr(e.status, 'value') else e.status}]"
                for e in client.get_recent_executions(limit=parsed.limit)
            ]
        if parsed.activity_type in ("all", "models"):
            recent_models = client.get_recent_models(limit=parsed.limit)
            sections["models"] = [f"{m.name} ({m.execution_count} runs)" for m in recent_models]
        lines: list[str] = []
        for key in ("benchmarks", "executions", "models"):
            if key in sections:
                lines.append(f"{key}: " + "; ".join(sections[key][:15]))
        return _ok("Recent activity — " + " | ".join(lines), sections)


class GetDashboardTool(BaseTool):
    name = "get_dashboard"
    description = "Show the workspace dashboard summary (run counters, platform resource counts)."
    parameters_schema = {"type": "object", "properties": {}, "required": []}

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        snapshot = client.get_dashboard()
        s = snapshot.summary
        return _ok(
            f"Runs: {s.active_runs_count} active, {s.total_runs_count} total; "
            f"Platform: {snapshot.hierarchy.benchmarks} benchmarks, "
            f"{snapshot.hierarchy.models} models",
            {"summary": s.model_dump(), "hierarchy": snapshot.hierarchy.model_dump()},
        )


class GetHealthTool(BaseTool):
    name = "get_health"
    description = "Check Atlas API health (api status, liveness, readiness)."
    parameters_schema = {"type": "object", "properties": {}, "required": []}

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        health = client.health_summary()
        return _ok(
            f"API {health.status} (version {health.version})",
            {"api_status": health.status, "version": health.version},
        )


class WhoAmITool(BaseTool):
    name = "whoami"
    description = "Show the currently authenticated user (email, name, org)."
    parameters_schema = {"type": "object", "properties": {}, "required": []}

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        user = client.whoami()
        org = str(user.org_id) if user.org_id else "(none)"
        return _ok(
            f"Authenticated as {user.email} ({user.full_name}), org {org}",
            {
                "email": user.email,
                "full_name": user.full_name,
                "org_id": str(user.org_id) if user.org_id else None,
            },
        )
