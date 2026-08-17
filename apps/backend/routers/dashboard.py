from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone, UTC
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.dataset import Dataset
from atlas_db.models.evaluation import EvaluationResult
from atlas_db.models.execution import Execution, ExecutionStatus
from atlas_db.models.leaderboard import LeaderboardSnapshotEntry
from atlas_db.models.reporting import Report

router = APIRouter(tags=["Dashboard"])

_ACTIVE_STATUSES = {
    ExecutionStatus.RUNNING,
    ExecutionStatus.STARTING,
    ExecutionStatus.EVALUATING,
    ExecutionStatus.RETRYING,
    ExecutionStatus.CANCELLING,
}
_QUEUED_STATUSES = {ExecutionStatus.QUEUED, ExecutionStatus.SCHEDULED}
_FAILED_STATUSES = {ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT}


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _status_title(status: ExecutionStatus) -> str:
    if status == ExecutionStatus.TIMED_OUT:
        return "Failed"
    return str(status.value).capitalize()


def _execution_item(execution: Execution, benchmark_name: str | None) -> dict[str, Any]:
    config = execution.execution_config or {}
    total = execution.total_items or 1
    done = min(execution.completed_items or 0, total)
    progress = 100 if execution.status == ExecutionStatus.COMPLETED else round(done / total * 100)
    return {
        "id": str(execution.id),
        "model": execution.target_model,
        "benchmark": benchmark_name or "Unknown",
        "status": _status_title(execution.status),
        "progress": progress,
        "is_verified": bool(config.get("is_verified", False)),
        "source": config.get("source", "real"),
    }


def _derive_provider(model_name: str) -> str:
    lowered = model_name.lower()
    if "gemini" in lowered:
        return "Google AI"
    if "gpt" in lowered:
        return "OpenAI"
    if "claude" in lowered:
        return "Anthropic"
    if "grok" in lowered:
        return "xAI"
    if "llama" in lowered or "qwen" in lowered or "mistral" in lowered or "deepseek" in lowered:
        return "Open Source"
    return "Unknown"


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
) -> dict[str, Any]:
    """Aggregated workspace dashboard: run counts, hierarchy, active jobs, activity, runtime and top capability."""
    status_counter = Counter(row[0] for row in db.query(Execution.status).all())

    active_count = sum(status_counter[s] for s in _ACTIVE_STATUSES)
    queued_count = sum(status_counter[s] for s in _QUEUED_STATUSES)
    completed_count = status_counter[ExecutionStatus.COMPLETED]
    failed_count = sum(status_counter[s] for s in _FAILED_STATUSES)
    cancelled_count = status_counter[ExecutionStatus.CANCELLED]
    total_count = sum(status_counter.values())

    models_count = db.query(func.count(distinct(Execution.target_model))).scalar() or 0
    benchmarks_count = db.query(func.count(Benchmark.id)).scalar() or 0
    datasets_count = db.query(func.count(Dataset.id)).scalar() or 0
    evaluations_count = db.query(func.count(EvaluationResult.id)).scalar() or 0
    reports_count = db.query(func.count(Report.id)).scalar() or 0

    recent_rows = (
        db.query(Execution, Benchmark.name)
        .outerjoin(BenchmarkVersion, BenchmarkVersion.id == Execution.benchmark_version_id)
        .outerjoin(Benchmark, Benchmark.id == BenchmarkVersion.benchmark_id)
        .order_by(Execution.created_at.desc())
        .limit(12)
        .all()
    )
    execution_items = [_execution_item(ex, name) for ex, name in recent_rows]

    running_jobs = [
        item
        for item in execution_items
        if item["status"]
        in {"Running", "Starting", "Evaluating", "Retrying", "Cancelling", "Queued", "Scheduled"}
    ]
    recent_verified_runs = [item for item in execution_items if item["is_verified"]]

    activity: list[dict[str, Any]] = []
    for ex, name in recent_rows:
        benchmark_label = name or "benchmark"
        if ex.status == ExecutionStatus.COMPLETED:
            activity.append(
                {
                    "id": f"ex-completed-{ex.id}",
                    "type": "evaluation_completed",
                    "title": f"{ex.target_model} completed on {benchmark_label}",
                    "description": f"Run {ex.id} finished with {_execution_item(ex, name)['progress']}% progress.",
                    "timestamp": _iso(ex.completed_at or ex.created_at) or "",
                }
            )
        else:
            activity.append(
                {
                    "id": f"ex-{ex.id}",
                    "type": "evaluation_started",
                    "title": f"{ex.target_model} started on {benchmark_label}",
                    "description": f"Run {ex.id} is currently {_status_title(ex.status)}.",
                    "timestamp": _iso(ex.started_at or ex.created_at) or "",
                }
            )

    for report_row in (
        db.query(Report, Report.name).order_by(Report.created_at.desc()).limit(3).all()
    ):
        report = report_row[0]
        activity.append(
            {
                "id": f"report-{report.id}",
                "type": "report_generated",
                "title": f"Report generated: {report.name}",
                "description": f"Execution run report {report.name} is available.",
                "timestamp": _iso(report.created_at) or "",
            }
        )

    duration_seconds: list[float] = []
    for started_at, completed_at in (
        db.query(Execution.started_at, Execution.completed_at)
        .filter(Execution.status == ExecutionStatus.COMPLETED)
        .all()
    ):
        if started_at and completed_at:
            delta = (completed_at - started_at).total_seconds()
            if delta >= 0:
                duration_seconds.append(delta)
    avg_runtime_sec = (
        round(sum(duration_seconds) / len(duration_seconds), 1) if duration_seconds else 0.0
    )

    top_entry = (
        db.query(LeaderboardSnapshotEntry).order_by(LeaderboardSnapshotEntry.rank.asc()).first()
    )

    dashboard: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "summary": {
            "active_runs_count": active_count,
            "queued_runs_count": queued_count,
            "completed_runs_count": completed_count,
            "failed_runs_count": failed_count,
            "cancelled_runs_count": cancelled_count,
            "total_runs_count": total_count,
        },
        "hierarchy": {
            "models": models_count,
            "benchmarks": benchmarks_count,
            "datasets": datasets_count,
            "evaluations": evaluations_count,
            "reports": reports_count,
        },
        "running_jobs": running_jobs,
        "recent_verified_runs": recent_verified_runs,
        "active_executions": execution_items,
        "activity": activity,
        "runtime": {
            "engine_status": "healthy",
            "total_benchmarks": benchmarks_count,
            "total_evaluations": evaluations_count,
            "total_models": models_count,
            "avg_runtime_sec": avg_runtime_sec,
        },
    }

    if top_entry:
        capabilities: list[dict[str, Any]] = []
        by_domain: dict[str, list[float]] = {}
        cap_rows = (
            db.query(Execution, Benchmark.domain)
            .outerjoin(BenchmarkVersion, BenchmarkVersion.id == Execution.benchmark_version_id)
            .outerjoin(Benchmark, Benchmark.id == BenchmarkVersion.benchmark_id)
            .filter(
                Execution.target_model == top_entry.target_model,
                Execution.status == ExecutionStatus.COMPLETED,
            )
            .all()
        )
        for execution, domain in cap_rows:
            score = (execution.execution_config or {}).get("pass_at_1")
            if score is not None and domain:
                by_domain.setdefault(domain, []).append(float(score))
        capabilities = [
            {"domain": domain, "score": round(sum(scores) / len(scores), 1)}
            for domain, scores in sorted(by_domain.items())
        ]
        dashboard["capability"] = {
            "model_name": top_entry.target_model,
            "provider": _derive_provider(top_entry.target_model),
            "rank": top_entry.rank,
            "score": top_entry.score,
            "capabilities": capabilities,
        }

    return dashboard
