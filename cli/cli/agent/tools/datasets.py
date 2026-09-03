"""Client-side agent dataset-authoring tools (v3.3).

Each tool validates its arguments, delegates to a corresponding ``AtlasClient``
dataset method, and returns a compact :class:`ToolResult`.

Confirmation model:
    * READ tools (``list_datasets`` / ``get_dataset``) never confirm.
    * WRITE authoring tools (``create_dataset`` / ``update_dataset`` /
      ``upload_dataset_tasks`` / ``validate_dataset``) are gated by the standard
      REPL confirmation (``required_permission = WRITE``).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from cli.agent.tools.base import AgentPermission, BaseTool, ToolResult
from cli.agent.tools.library import _ok, _parse


class _TaskItem(BaseModel):
    input: Any
    expected_output: Any
    description: str | None = None


class _ProjectArgs(BaseModel):
    project_id: str


class _DatasetArgs(BaseModel):
    project_id: str
    dataset_id: str


class _CreateDatasetArgs(BaseModel):
    project_id: str
    name: str = Field(..., max_length=255)
    description: str | None = None
    version_string: str = "v1.0.0"
    tasks: list[_TaskItem] | None = None


class _UpdateDatasetArgs(BaseModel):
    project_id: str
    dataset_id: str
    name: str | None = Field(None, max_length=255)
    description: str | None = None


class _UploadTasksArgs(BaseModel):
    project_id: str
    dataset_id: str
    version_string: str = "v1.0.0"
    tasks: list[_TaskItem]


def _tasks_to_payload(tasks: list[_TaskItem] | None) -> list[dict[str, Any]] | None:
    if tasks is None:
        return None
    return [
        {
            "input": t.input,
            "expected_output": t.expected_output,
            **({"description": t.description} if t.description else {}),
        }
        for t in tasks
    ]


# ── reading (READ) ────────────────────────────────────────────────────────


class ListDatasetsTool(BaseTool):
    name = "list_datasets"
    description = (
        "List datasets in a project (by its id from list_projects). Returns "
        "dataset ids, names, statuses, and task counts."
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
        datasets = client.list_datasets(parsed.project_id)
        items = [
            {
                "id": str(d.id),
                "name": d.name,
                "status": d.status,
                "total_tasks": d.total_tasks,
            }
            for d in datasets
        ]
        summary = "; ".join(f"{it['name']} ({it['id']})" for it in items[:15])
        return _ok(
            f"{len(items)} dataset(s): {summary}",
            {"items": items, "total": len(items)},
        )


class GetDatasetTool(BaseTool):
    name = "get_dataset"
    description = (
        "Fetch a single dataset by id (within a project). Returns metadata, "
        "versions, and a sample of its tasks."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "dataset_id": {"type": "string", "description": "Dataset UUID."},
        },
        "required": ["project_id", "dataset_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_DatasetArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        ds = client.get_dataset(parsed.project_id, parsed.dataset_id)
        versions = [
            {
                "id": str(v.id),
                "version_string": v.version_string,
                "lifecycle": v.lifecycle,
            }
            for v in (ds.versions or [])
        ]
        return _ok(
            f"Dataset {ds.name} ({ds.id}): {ds.total_tasks} task(s), "
            f"{len(versions)} version(s)",
            {
                "id": str(ds.id),
                "name": ds.name,
                "status": ds.status,
                "total_tasks": ds.total_tasks,
                "versions": versions,
                "sample_tasks": ds.sample_tasks,
            },
        )


# ── authoring (WRITE) ─────────────────────────────────────────────────────


class CreateDatasetTool(BaseTool):
    name = "create_dataset"
    description = (
        "Create a new dataset in a project. MUTATING: requires confirmation. "
        "Optionally seeds it with tasks (each {input, expected_output, "
        "description}). Takes a project_id (from list_projects), a name, and "
        "optional description / tasks."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "name": {"type": "string", "description": "Dataset name."},
            "description": {"type": "string", "description": "Optional description."},
            "version_string": {
                "type": "string",
                "description": "Initial version label.",
                "default": "v1.0.0",
            },
            "tasks": {
                "type": "array",
                "items": {"type": "object"},
                "description": (
                    "Optional initial tasks, each {input, expected_output, description}."
                ),
            },
        },
        "required": ["project_id", "name"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_CreateDatasetArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        ds = client.create_dataset(
            parsed.project_id,
            name=parsed.name,
            description=parsed.description,
            version_string=parsed.version_string,
            tasks=_tasks_to_payload(parsed.tasks),
        )
        return _ok(
            f"Created dataset {ds.id} ({ds.name}) in project {parsed.project_id} "
            f"[{ds.total_tasks} task(s)]",
            {
                "dataset_id": str(ds.id),
                "name": ds.name,
                "status": ds.status,
                "total_tasks": ds.total_tasks,
            },
        )


class UpdateDatasetTool(BaseTool):
    name = "update_dataset"
    description = (
        "Update a dataset's name/description by its id. MUTATING: requires "
        "confirmation. Only provided fields change."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "dataset_id": {"type": "string", "description": "Dataset UUID."},
            "name": {"type": "string", "description": "New name."},
            "description": {"type": "string", "description": "New description."},
        },
        "required": ["project_id", "dataset_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_UpdateDatasetArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        if parsed.name is None and parsed.description is None:
            return ToolResult(ok=False, summary="no fields provided to update", error="no-op")
        ds = client.update_dataset(
            parsed.project_id,
            parsed.dataset_id,
            name=parsed.name,
            description=parsed.description,
        )
        return _ok(
            f"Updated dataset {parsed.dataset_id} -> name {ds.name}",
            {"dataset_id": str(ds.id), "name": ds.name},
        )


class UploadDatasetTasksTool(BaseTool):
    name = "upload_dataset_tasks"
    description = (
        "Replace a dataset's tasks as a fresh version. MUTATING: requires "
        "confirmation. Takes tasks (each {input, expected_output, description}) "
        "and an optional version_string."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "dataset_id": {"type": "string", "description": "Dataset UUID."},
            "version_string": {
                "type": "string",
                "description": "New version label.",
                "default": "v1.0.0",
            },
            "tasks": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Tasks to upload, each {input, expected_output, description}.",
            },
        },
        "required": ["project_id", "dataset_id", "tasks"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_UploadTasksArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        payload = _tasks_to_payload(parsed.tasks)
        if not payload:
            return ToolResult(ok=False, summary="no tasks provided", error="no-op")
        version = client.upload_dataset_tasks(
            parsed.project_id,
            parsed.dataset_id,
            payload,
            version_string=parsed.version_string,
        )
        return _ok(
            f"Uploaded {len(payload)} task(s) as version {version.id} "
            f"({version.version_string}) for dataset {parsed.dataset_id}",
            {
                "version_id": str(version.id),
                "version_string": version.version_string,
                "lifecycle": version.lifecycle,
                "task_count": len(payload),
            },
        )


class ValidateDatasetTool(BaseTool):
    name = "validate_dataset"
    description = (
        "Validate a dataset's latest version (checks it has tasks with test "
        "cases). MUTATING: updates validation state. Requires confirmation."
    )
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project UUID."},
            "dataset_id": {"type": "string", "description": "Dataset UUID."},
        },
        "required": ["project_id", "dataset_id"],
    }

    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        parsed = _parse(_DatasetArgs, kwargs)
        if isinstance(parsed, ValidationError):
            return ToolResult(ok=False, summary="invalid arguments", error=str(parsed))
        result = client.validate_dataset(parsed.project_id, parsed.dataset_id)
        return _ok(
            f"Dataset {parsed.dataset_id} validation: {'VALID' if result.valid else 'FAILED'} "
            f"({result.task_count} task(s)) — " + "; ".join(result.messages),
            {
                "dataset_id": str(result.dataset_id),
                "lifecycle": result.lifecycle,
                "valid": result.valid,
                "task_count": result.task_count,
                "messages": result.messages,
            },
        )
