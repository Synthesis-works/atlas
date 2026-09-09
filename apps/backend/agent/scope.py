"""Server-side, identity-scoped authorization gate for agent tool execution.

P1 hard gate. Every tool call made by an *owned* AgentTask (one carrying the
JWT-derived ``created_by_user_id`` / ``organization_id`` stamps) is checked
here BEFORE it touches the database. Enforces:

- resource scoping: a tool may only operate on resources (benchmarks, datasets,
  executions) whose owning project the caller is an active member of,
- permission scoping: READ tools are open to any active membership role;
  WRITE / EXECUTE / PUBLISH tools are restricted to OWNER / ADMIN / MEMBER,
- project anchoring: mutation tools that would create a new resource
  (``create_benchmark``) must target the task's anchored ``project_id`` - never
  the legacy shared-fallback UUID that used to funnel every agent write into a
  single global bucket.

Ownership comes from the task stamps stamped by the API router from the caller's
JWT. Tasks constructed directly without those stamps (legacy rows, worker-
internal constructions) are never surfaced to any API user and carry no
enforceable caller; they are left un-gated to preserve existing internal
behavior.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from apps.backend.agent.state import AgentPermission, AgentTask
from apps.backend.agent.tools.base import BaseTool
from apps.backend.authz import ProjectAuthorizationService
from atlas_db.models.core import OrganizationRole

# Read-level tool access requires any active membership role; mutations
# (create / execute / publish) require an owner/admin/member.
READ_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
    OrganizationRole.VIEWER,
]
MUTATE_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
]

# Legacy global scratch project that pre-P1 tools fell back to when no project
# was anchored. Owned tasks must never write here.
SHARED_FALLBACK_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class ToolScopeDenied(RuntimeError):
    """Raised when a tool call falls outside the caller's authorized scope."""


# Tool -> argument names holding the resource identifiers that resolve to an
# owning project. The resolver walks each argument present and authorizes the
# caller on every resolved project.
_RESOURCE_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "get_benchmark": ("benchmark_id",),
    "create_dataset": ("benchmark_id",),
    "get_dataset": ("dataset_id",),
    "update_dataset": ("dataset_id",),
    "validate_benchmark_dataset": ("dataset_id",),
    "create_evaluation_case": ("dataset_id",),
    "run_benchmark": ("benchmark_version_id", "dataset_version_id"),
    "get_run_status": ("execution_id",),
    "evaluate_run": ("execution_id",),
    "wait_for_runs": ("execution_ids",),
    "compare_results": ("execution_ids",),
    "generate_report": ("benchmark_id",),
}


def _unique(project_ids: list[uuid.UUID | None]) -> list[uuid.UUID]:
    return list(dict.fromkeys(pid for pid in project_ids if pid is not None))


class ToolScopeEnforcer:
    """Resolves the owning project(s) of a tool call and authorizes the caller."""

    def __init__(
        self, db: Session, authz_service: ProjectAuthorizationService | None = None
    ) -> None:
        self.db = db
        self._authz = authz_service or ProjectAuthorizationService(db)

    def enforce(
        self,
        task: AgentTask,
        tool: BaseTool,
        arguments: dict[str, Any],
    ) -> None:
        """Raise ``ToolScopeDenied`` if the task owner may not run this tool.

        Owned tasks (``created_by_user_id`` set) are always gated. Un-owned
        tasks skip the gate for internal compatibility.
        """
        user_id = task.created_by_user_id
        if user_id is None:
            return

        roles = (
            MUTATE_ROLES
            if tool.required_permission
            in (
                AgentPermission.WRITE,
                AgentPermission.EXECUTE,
                AgentPermission.PUBLISH,
            )
            else READ_ROLES
        )

        project_ids = self._resolve_project_ids(tool.name, arguments)
        if project_ids:
            for project_id in project_ids:
                self._authorize(user_id, project_id, roles)
            return

        # No resolvable target resource: mutation tools must still be anchored
        # to a project the caller can write to.
        if tool.required_permission in (
            AgentPermission.WRITE,
            AgentPermission.EXECUTE,
            AgentPermission.PUBLISH,
        ):
            if tool.name == "create_benchmark":
                if task.project_id is None:
                    raise ToolScopeDenied(
                        "Tool 'create_benchmark' requires a project-scoped task; "
                        "no project is anchored to this task."
                    )
                self._authorize(user_id, task.project_id, roles)
                return
            raise ToolScopeDenied(
                f"Tool '{tool.name}' could not be scoped to a project owned by the caller."
            )

    def _authorize(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        roles: list[OrganizationRole],
    ) -> None:
        try:
            self._authz.authorize_project_access(
                project_id=project_id,
                user_id=user_id,
                allowed_roles=roles,
            )
        except Exception as exc:  # HTTPException from the authz service
            raise ToolScopeDenied(
                f"Tool execution denied for task owner on project '{project_id}': {exc}"
            ) from exc

    def _resolve_project_ids(self, tool_name: str, arguments: dict[str, Any]) -> list[uuid.UUID]:
        arg_names = _RESOURCE_ARGUMENTS.get(tool_name, ())
        resolved: list[uuid.UUID | None] = []
        for name in arg_names:
            value = arguments.get(name)
            ids = value if isinstance(value, list) else [value]
            for raw_id in ids:
                if raw_id is None:
                    continue
                resolved.append(self._resolve_one(name, raw_id))
        return _unique(resolved)

    def _resolve_one(self, arg_name: str, raw_id: Any) -> uuid.UUID | None:
        try:
            resource_id = uuid.UUID(str(raw_id))
        except ValueError:
            return None

        if arg_name in ("benchmark_id", "benchmark_version_id"):
            return self._benchmark_project(
                resource_id, is_version=(arg_name == "benchmark_version_id")
            )
        if arg_name in ("dataset_id", "dataset_version_id"):
            return self._dataset_project(resource_id, is_version=(arg_name == "dataset_version_id"))
        if arg_name == "execution_id":
            return self._execution_project(resource_id)
        return None

    def _benchmark_project(self, resource_id: uuid.UUID, *, is_version: bool) -> uuid.UUID | None:
        from atlas_db.models.authoring import Benchmark, BenchmarkVersion

        if is_version:
            version = (
                self.db.query(BenchmarkVersion).filter(BenchmarkVersion.id == resource_id).first()
            )
            if version is None or version.benchmark_id is None:
                return None
            resource_id = uuid.UUID(str(version.benchmark_id))
        benchmark = self.db.query(Benchmark).filter(Benchmark.id == resource_id).first()
        return benchmark.project_id if benchmark else None

    def _dataset_project(self, resource_id: uuid.UUID, *, is_version: bool) -> uuid.UUID | None:
        from atlas_db.models.dataset import Dataset, DatasetVersion

        if is_version:
            version = self.db.query(DatasetVersion).filter(DatasetVersion.id == resource_id).first()
            if version is None or version.dataset_id is None:
                return None
            resource_id = uuid.UUID(str(version.dataset_id))
        dataset = self.db.query(Dataset).filter(Dataset.id == resource_id).first()
        return dataset.project_id if dataset else None

    def _execution_project(self, resource_id: uuid.UUID) -> uuid.UUID | None:
        from atlas_db.models.execution import Execution

        execution = self.db.query(Execution).filter(Execution.id == resource_id).first()
        return execution.project_id if execution else None
