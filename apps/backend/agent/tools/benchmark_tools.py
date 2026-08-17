import uuid
from typing import Any, Dict
from sqlalchemy.orm import Session

from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from apps.backend.agent.state import AgentPermission
from apps.backend.agent.tools.base import BaseTool


class SearchBenchmarksTool(BaseTool):
    name = "search_benchmarks"
    description = "Search existing benchmarks in Atlas by query string or category."
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query filter for benchmark name or objective.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of benchmarks to return (default 10).",
            },
        },
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        query = kwargs.get("query")
        if query is None:
            raise ValueError("query is required")
        limit = kwargs.get("limit")
        if limit is None:
            raise ValueError("limit is required")

        q = db.query(Benchmark)
        if query:
            q = q.filter(Benchmark.name.ilike(f"%{query}%"))
        results = q.limit(limit).all()
        return [
            {
                "id": str(b.id),
                "name": b.name,
                "objective": b.objective,
                "domain": b.domain,
                "status": b.status,
            }
            for b in results
        ]


class GetBenchmarkTool(BaseTool):
    name = "get_benchmark"
    description = "Retrieve detailed metadata and version history for a specific benchmark by ID."
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_id": {"type": "string", "description": "UUID of the benchmark to retrieve."},
        },
        "required": ["benchmark_id"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        benchmark_id = kwargs.get("benchmark_id")
        if benchmark_id is None:
            raise ValueError("benchmark_id is required")

        try:
            b_uuid = uuid.UUID(benchmark_id)
        except ValueError:
            return {"error": f"Invalid UUID string: '{benchmark_id}'"}

        bm = db.query(Benchmark).filter(Benchmark.id == b_uuid).first()
        if not bm:
            return {"error": f"Benchmark with ID '{benchmark_id}' not found."}

        versions = db.query(BenchmarkVersion).filter(BenchmarkVersion.benchmark_id == b_uuid).all()
        return {
            "id": str(bm.id),
            "name": bm.name,
            "objective": bm.objective,
            "domain": bm.domain,
            "type": bm.type,
            "status": bm.status,
            "versions": [
                {"version_id": str(v.id), "version_number": getattr(v, "version_number", "v1.0")}
                for v in versions
            ],
        }


class CreateBenchmarkTool(BaseTool):
    name = "create_benchmark"
    description = "Create a new benchmark specification in Atlas."
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Benchmark title/name."},
            "description": {
                "type": "string",
                "description": "Objective or description of what the benchmark tests.",
            },
            "task_type": {
                "type": "string",
                "description": "Task classification (e.g. security_code_audit, reasoning).",
            },
            "evaluation_method": {
                "type": "string",
                "description": "Evaluation strategy (e.g. exact_match, llm_judge).",
            },
        },
        "required": ["name"],
    }

    def execute(
        self,
        db: Session,
        name: str,
        description: str = "",
        task_type: str = "general",
        evaluation_method: str = "exact_match",
        **kwargs: Any,
    ) -> Any:
        proj_id = kwargs.get("project_id") or uuid.UUID("00000000-0000-0000-0000-000000000001")
        bm_id = uuid.uuid4()
        version_id = uuid.uuid4()

        bm = Benchmark(
            id=bm_id,
            project_id=proj_id,
            name=name,
            objective=description,
            type=task_type,
            status="DRAFT",
        )
        db.add(bm)

        # Create initial BenchmarkVersion
        version = BenchmarkVersion(
            id=version_id,
            benchmark_id=bm_id,
            version_string="1.0.0",
        )
        db.add(version)

        try:
            db.commit()
        except Exception:
            db.rollback()

        return {
            "id": str(bm_id),
            "version_id": str(version_id),
            "name": bm.name,
            "status": bm.status,
            "message": "Benchmark created successfully.",
        }
