"""Client-side agent benchmark-authoring tools (v3.2).

Every authoring tool validates its arguments, delegates to a corresponding
``AtlasClient`` writer/discovery method, and returns a compact
:class:`ToolResult`.

Confirmation model:
    * READ discovery tools (``list_organizations`` / ``list_projects``) never
      confirm.
    * WRITE authoring tools (create/update/publish) are gated by the standard
      REPL confirmation (``required_permission = WRITE``).
    * Destructive tools (delete/archive) additionally set ``destructive=True``
      so the REPL issues a stronger double-confirm.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from cli.agent.tools.base import AgentPermission, BaseTool, ToolResult
from cli.agent.tools.library import _ok, _parse


class _CreateBenchmarkArgs(BaseModel):
    project_id: str
    name: str = Field(..., max_length=255)
    objective: str | None = None
    category_ids: list[str] | None = None
    capability_ids: list[str] | None = None


class _UpdateBenchmarkArgs(BaseModel):
    benchmark_id: str
    name: str | None = Field(None, max_length=255)
    objective: str | None = None
    category_ids: list[str] | None = None
    capability_ids: list[str] | None = None


class _BenchmarkIdArgs(BaseModel):
    benchmark_id: str


class _CreateVersionArgs(BaseModel):
    benchmark_id: str
    version_string: str = Field(..., max_length=255)
    dataset_version_ids: list[str] | None = None
    evaluation_strategy_id: str | None = None


class _VersionIdArgs(BaseModel):
    version_id: str


class _OrgArgs(BaseModel):
    org_id: str


# ── discovery (READ) ─────────────────────────────────────────────────────


class ListOrganizationsTool(BaseTool):
    name = "list_organizations"
    description = "List the organizations the current user belongs to. Use to discover an org id."
    parameters_schema = {"type": "object", "properties": {}, "required": []}

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        orgs = client.list_organizations()
        items = [{"id": str(o.id), "name": o.name} for o in orgs]
        summary = "; ".join(f"{o['name']} ({o['id']})" for o in items[:15])
        return _ok(
            f"{len(items)} organization(s): {summary}",
            {"items": items, "total": len(items)},
        )


class ListProjectsTool(BaseTool):
    name = "list_projects"
    description = (
        "List projects in an organization (by its id from list_organizations). "
        "A project id is required by create_benchmark."
    )
    parameters_schema = {
        "type": "object",
        "properties": {"org_id": {"type": "string", "description": "Organization UUID."}},
        "required": ["org_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_OrgArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        projects = client.list_projects(parsed.org_id)
        items = [{"id": str(p.id), "name": p.name} for p in projects]
        summary = "; ".join(f"{p['name']} ({p['id']})" for p in items[:15])
        return _ok(f"{len(items)} project(s): {summary}", {"items": items, "total": len(items)})


# ── authoring (WRITE) ────────────────────────────────────────────────────


class CreateBenchmarkTool(BaseTool):
    name = "create_benchmark"
    description = (
        "Create a new benchmark in a project. MUTATING: requires confirmation. "
        "Takes a project_id (from list_projects), a name, and optional objective, "
        "category_ids, capability_ids."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID to create under."},
            "name": {"type": "string", "description": "Benchmark name."},
            "objective": {"type": "string", "description": "Optional benchmark objective."},
            "category_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional category UUIDs.",
            },
            "capability_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional capability UUIDs.",
            },
        },
        "required": ["project_id", "name"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_CreateBenchmarkArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        benchmark = client.create_benchmark(
            parsed.project_id,
            name=parsed.name,
            objective=parsed.objective,
            category_ids=parsed.category_ids,
            capability_ids=parsed.capability_ids,
        )
        return _ok(
            f"Created benchmark {benchmark.id} ({benchmark.name}) in project "
            f"{parsed.project_id} [state {benchmark.state}]",
            {"benchmark_id": str(benchmark.id), "name": benchmark.name, "state": benchmark.state},
        )


class UpdateBenchmarkTool(BaseTool):
    name = "update_benchmark"
    description = (
        "Update name/objective/categories/capabilities of a benchmark by its id. "
        "MUTATING: requires confirmation. Only provided fields change."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_id": {"type": "string", "description": "Benchmark UUID."},
            "name": {"type": "string", "description": "New name."},
            "objective": {"type": "string", "description": "New objective."},
            "category_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Replace category UUIDs.",
            },
            "capability_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Replace capability UUIDs.",
            },
        },
        "required": ["benchmark_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_UpdateBenchmarkArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        if not all(
            v is None
            for v in (parsed.name, parsed.objective, parsed.category_ids, parsed.capability_ids)
        ):
            benchmark = client.update_benchmark(
                parsed.benchmark_id,
                name=parsed.name,
                objective=parsed.objective,
                category_ids=parsed.category_ids,
                capability_ids=parsed.capability_ids,
            )
            return _ok(
                f"Updated benchmark {parsed.benchmark_id} -> name {benchmark.name}",
                {"benchmark_id": str(benchmark.id), "name": benchmark.name},
            )
        return ToolResult(ok=False, summary="no fields provided to update", error="no-op")


class CreateBenchmarkVersionTool(BaseTool):
    name = "create_benchmark_version"
    description = (
        "Create a new version of a benchmark. MUTATING: requires confirmation. "
        "Takes a benchmark_id (from list_benchmarks), a version_string, and optional "
        "dataset_version_ids / evaluation_strategy_id."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_id": {"type": "string", "description": "Benchmark UUID."},
            "version_string": {"type": "string", "description": "Version label (e.g. 1.0.0)."},
            "dataset_version_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional dataset version UUIDs.",
            },
            "evaluation_strategy_id": {
                "type": "string",
                "description": "Optional evaluation strategy UUID.",
            },
        },
        "required": ["benchmark_id", "version_string"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_CreateVersionArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        version = client.create_benchmark_version(
            parsed.benchmark_id,
            version_string=parsed.version_string,
            dataset_version_ids=parsed.dataset_version_ids,
            evaluation_strategy_id=parsed.evaluation_strategy_id,
        )
        return _ok(
            f"Created version {version.id} ({version.version_string}) for benchmark "
            f"{parsed.benchmark_id} [state {version.state}]",
            {
                "version_id": str(version.id),
                "version_string": version.version_string,
                "state": version.state,
            },
        )


class PublishBenchmarkVersionTool(BaseTool):
    name = "publish_benchmark_version"
    description = (
        "Publish a benchmark version (requires ADMIN/OWNER). MUTATING: requires "
        "confirmation. Takes a version_id (from get_benchmark_versions)."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {"version_id": {"type": "string", "description": "Benchmark version UUID."}},
        "required": ["version_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_VersionIdArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        client.publish_benchmark_version(parsed.version_id)
        return _ok(
            f"Published benchmark version {parsed.version_id}",
            {"version_id": parsed.version_id, "published": True},
        )


class ArchiveBenchmarkVersionTool(BaseTool):
    name = "archive_benchmark_version"
    description = (
        "Archive a benchmark version (requires ADMIN/OWNER). DESTRUCTIVE/MUTATING: "
        "requires confirmation. Takes a version_id."
    )
    required_permission = AgentPermission.WRITE
    destructive = True
    parameters_schema = {
        "type": "object",
        "properties": {"version_id": {"type": "string", "description": "Benchmark version UUID."}},
        "required": ["version_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_VersionIdArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        client.archive_benchmark_version(parsed.version_id)
        return _ok(
            f"Archived benchmark version {parsed.version_id}",
            {"version_id": parsed.version_id, "archived": True},
        )


class DeleteBenchmarkTool(BaseTool):
    name = "delete_benchmark"
    description = (
        "Delete a benchmark permanently by its id. DESTRUCTIVE/MUTATING: requires "
        "confirmation. This cannot be undone."
    )
    required_permission = AgentPermission.WRITE
    destructive = True
    parameters_schema = {
        "type": "object",
        "properties": {"benchmark_id": {"type": "string", "description": "Benchmark UUID."}},
        "required": ["benchmark_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_BenchmarkIdArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        client.delete_benchmark(parsed.benchmark_id)
        return _ok(
            f"Deleted benchmark {parsed.benchmark_id}",
            {"benchmark_id": parsed.benchmark_id, "deleted": True},
        )
