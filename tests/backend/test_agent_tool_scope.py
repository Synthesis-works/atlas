"""P1 Tests: identity-scoped tool authorization gate.

These drive ``ToolScopeEnforcer`` directly (not the whole agent loop) with a
recording fake ``ProjectAuthorizationService``. They verify the two-stamp
guarantee that is the core of the "hosted conversational session" security
model:

- a tool may only be executed when the owning resource's project authorizes
  the task owner (never a different user's / org's data),
- READ tools accept any active membership role; WRITE/EXECUTE/PUBLISH tools
  require owner/admin/member,
- mutation tools that resolve no target resource (``create_benchmark``) are
  denied unless they are anchored to a project the caller owns,
- un-owned (legacy/internal) tasks are left un-gated so existing worker-side
  construction keeps working.
"""

import uuid
from dataclasses import dataclass, field

import pytest

from apps.backend.agent.scope import SHARED_FALLBACK_PROJECT_ID, ToolScopeDenied, ToolScopeEnforcer
from apps.backend.agent.state import AgentPermission, AgentTask
from apps.backend.agent.tools.registry import ToolRegistry
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.core import OrganizationRole, Project
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.execution import Execution, ExecutionStatus

READ_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
    OrganizationRole.VIEWER,
]
MUTATE_ROLES = [OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER]


@dataclass
class RecordingAuthz:
    allow: bool = True
    allowed_at: list = field(default_factory=list)

    def authorize_project_access(self, project_id, user_id, allowed_roles):
        record = (str(project_id), str(user_id), [r.value for r in allowed_roles])
        self.allowed_at.append(record)
        if not self.allow:
            raise AssertionError("denied")
        return record


def _registry():
    return ToolRegistry()


def _task(*, created_by=None, org=None, project_id=None):
    task = AgentTask(goal="g", granted_permissions=[AgentPermission.READ, AgentPermission.WRITE])
    task.created_by_user_id = created_by
    task.organization_id = org
    task.project_id = project_id
    return task


def _tool(name):
    return _registry().get_tool(name)


def _enforcer(db, authz=None, allow=True):
    authz = authz or RecordingAuthz(allow=allow)
    return ToolScopeEnforcer(db, authz_service=authz), authz


def _seed_project(db, org_id, *, name="scope proj"):
    project = Project(org_id=org_id, name=name, slug=f"scope-{uuid.uuid4().hex[:8]}")
    db.add(project)
    db.flush()
    return project


def _seed_benchmark(db, project_id):
    bm = Benchmark(
        id=uuid.uuid4(), project_id=project_id, name=f"bm-{uuid.uuid4().hex[:6]}", status="DRAFT"
    )
    db.add(bm)
    db.flush()
    version = BenchmarkVersion(
        id=uuid.uuid4(),
        benchmark_id=bm.id,
        version_string="1.0.0",
        evaluation_strategy_id=uuid.uuid4(),
    )
    db.add(version)
    db.flush()
    return bm, version


def _seed_dataset(db, project_id):
    ds = Dataset(id=uuid.uuid4(), project_id=project_id, name=f"ds-{uuid.uuid4().hex[:6]}")
    db.add(ds)
    db.flush()
    version = DatasetVersion(
        id=uuid.uuid4(), dataset_id=ds.id, version_string="1.0.0", storage_path="s3://scope-ds"
    )
    db.add(version)
    db.flush()
    return ds, version


def _seed_execution(db, project_id):
    execution = Execution(
        id=uuid.uuid4(),
        project_id=project_id,
        benchmark_version_id=uuid.uuid4(),
        target_model="provider/mock",
        status=ExecutionStatus.COMPLETED,
        submitted_by_id=uuid.uuid4(),
    )
    db.add(execution)
    db.flush()
    return execution


# --- un-owned (legacy) tasks are never gated --------------------------------


def test_ownerless_task_is_not_gated(db_session):
    enforcer, authz = _enforcer(db_session)
    task = _task()
    enforcer.enforce(task, _tool("get_benchmark"), {"benchmark_id": str(uuid.uuid4())})
    assert authz.allowed_at == []


# --- deny writes to other users' / orgs' data -------------------------------


def test_get_benchmark_denied_for_foreign_org(db_session):
    project_a = _seed_project(db_session, uuid.uuid4())
    bm, _ = _seed_benchmark(db_session, project_a.id)
    user = uuid.uuid4()

    enforcer, authz = _enforcer(db_session, allow=False)
    task = _task(created_by=user, org=uuid.uuid4())
    with pytest.raises(ToolScopeDenied):
        enforcer.enforce(task, _tool("get_benchmark"), {"benchmark_id": str(bm.id)})
    assert authz.allowed_at[0][0] == str(project_a.id)
    assert authz.allowed_at[0][1] == str(user)


# --- READ is open to all four roles, mutations require member+ --------------


def test_read_tool_authorizes_all_roles(db_session):
    project = _seed_project(db_session, uuid.uuid4())
    bm, _ = _seed_benchmark(db_session, project.id)
    user = uuid.uuid4()

    for role in READ_ROLES:
        enforcer, authz = _enforcer(db_session)
        task = _task(created_by=user, org=project.org_id)
        enforcer.enforce(task, _tool("get_benchmark"), {"benchmark_id": str(bm.id)})
        assert authz.allowed_at[-1][2] == [r.value for r in READ_ROLES]


def test_mutate_tool_requests_member_plus_roles(db_session):
    project = _seed_project(db_session, uuid.uuid4())
    bm, version = _seed_benchmark(db_session, project.id)
    user = uuid.uuid4()

    # The enforcer must request the tighter (mutate) role set for WRITE /
    # EXECUTE tools, regardless of what any caller is.
    enforcer, authz = _enforcer(db_session, allow=True)
    task = _task(created_by=user, org=project.org_id)
    enforcer.enforce(task, _tool("run_benchmark"), {"benchmark_version_id": str(version.id)})
    assert authz.allowed_at[-1][2] == [r.value for r in MUTATE_ROLES]


# --- dataset / execution resolution -----------------------------------------


def test_dataset_and_execution_resolution(db_session):
    project = _seed_project(db_session, uuid.uuid4())
    ds, ds_version = _seed_dataset(db_session, project.id)
    execution = _seed_execution(db_session, project.id)
    user = uuid.uuid4()

    task = _task(created_by=user, org=project.org_id)
    for tool_name, args in [
        ("get_dataset", {"dataset_id": str(ds.id)}),
        ("update_dataset", {"dataset_id": str(ds.id)}),
        ("get_run_status", {"execution_id": str(execution.id)}),
    ]:
        enforcer, authz = _enforcer(db_session, allow=True)
        task.created_by_user_id = user
        enforcer.enforce(task, _tool(tool_name), args)
        assert authz.allowed_at[-1][0] == str(project.id), tool_name


def test_unresolvable_target_denied_for_mutation(db_session):
    user = uuid.uuid4()
    task = _task(created_by=user, org=uuid.uuid4(), project_id=None)
    enforcer, authz = _enforcer(db_session, allow=True)
    with pytest.raises(ToolScopeDenied):
        enforcer.enforce(task, _tool("create_benchmark"), {"name": "orphan"})


def test_create_benchmark_requires_project_anchor(db_session):
    user = uuid.uuid4()
    project = _seed_project(db_session, uuid.uuid4())
    task = _task(created_by=user, org=project.org_id, project_id=project.id)
    enforcer, authz = _enforcer(db_session, allow=True)
    enforcer.enforce(task, _tool("create_benchmark"), {"name": "anchored"})
    assert authz.allowed_at[-1][0] == str(project.id)


def test_shared_fallback_project_is_never_implicitly_used(db_session):
    """An owned mutation with no anchor must not silently fall back to the
    shared global scratch project."""
    user = uuid.uuid4()
    task = _task(created_by=user, org=uuid.uuid4(), project_id=SHARED_FALLBACK_PROJECT_ID)
    enforcer, authz = _enforcer(db_session, allow=True)
    # Even if the task is (incorrectly) anchored to the fallback, run_benchmark
    # with no resolvable resource must be denied rather than writing globally.
    with pytest.raises(ToolScopeDenied):
        enforcer.enforce(task, _tool("run_benchmark"), {"benchmark_version_id": str(uuid.uuid4())})
