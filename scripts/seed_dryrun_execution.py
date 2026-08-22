"""Seed a fully synthetic benchmark execution for CI dry-runs.

Creates the schema on an empty database and inserts the minimal model graph
(Project -> Benchmark -> BenchmarkVersion -> Dataset -> DatasetVersion ->
Task -> Prompt -> TestCase -> Execution) using a ``mock`` target model so the
benchmark container produces ``mocked_output`` without any provider credentials.

Prints ``execution_id=<uuid>`` on stdout (GitHub Actions step-output friendly).
"""

from __future__ import annotations

import sys
import uuid

REPO_ROOT = __file__.rsplit("\\scripts", 1)[0].rsplit("/scripts", 1)[0]
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, REPO_ROOT + "/packages/database")

from atlas_db.core.session import SessionLocal  # noqa: E402


def main() -> int:
    # Import all model modules so Base.metadata is complete before create_all.
    # This includes the execution-engine persistence family (ee_executions,
    # execution_attempts, ...) that ExecutionWorker.status-mirrors alongside
    # the core tables - matching what the alembic baseline creates.
    import atlas_db.models  # noqa: F401
    import packages.execution_engine.persistence.models  # noqa: F401
    from atlas_db.core.base import Base
    from atlas_db.models.authoring import Benchmark, BenchmarkVersion
    from atlas_db.models.core import Project
    from atlas_db.models.dataset import Dataset, DatasetVersion
    from atlas_db.models.execution import Execution, ExecutionStatus
    from atlas_db.models.tasks import Prompt, Task, TestCase

    engine = SessionLocal.kw["bind"]
    Base.metadata.create_all(engine)

    project_id = uuid.uuid4()
    benchmark_version_id = uuid.uuid4()
    dataset_version_id = uuid.uuid4()

    with SessionLocal() as db:
        project = Project(id=project_id, name="dryrun-project", slug=f"dryrun-{project_id}")
        db.add(project)
        db.flush()

        benchmark = Benchmark(project_id=project_id, name="dryrun-benchmark")
        db.add(benchmark)
        db.flush()

        dataset = Dataset(project_id=project_id, name="dryrun-dataset")
        db.add(dataset)
        db.flush()

        dataset_version = DatasetVersion(
            id=dataset_version_id,
            dataset_id=dataset.id,
            version_string="v1",
            storage_path=f"s3://dryrun/{dataset_version_id}",
        )
        db.add(dataset_version)
        db.flush()

        benchmark_version = BenchmarkVersion(
            id=benchmark_version_id,
            benchmark_id=benchmark.id,
            version_string="v1",
            primary_dataset_version_id=dataset_version_id,
        )
        benchmark_version.dataset_versions.append(dataset_version)
        db.add(benchmark_version)
        db.flush()

        task = Task(dataset_version_id=dataset_version_id, name="echo-task")
        db.add(task)
        db.flush()

        db.add(Prompt(task_id=task.id, template="Echo {text}"))
        db.flush()

        tc = TestCase(
            task_id=task.id,
            dataset_version_id=dataset_version_id,
            input_data={"text": "hello-dryrun"},
            expected_output={"text": "hello-dryrun"},
        )
        db.add(tc)
        db.flush()

        execution = Execution(
            project_id=project_id,
            benchmark_version_id=benchmark_version_id,
            dataset_version_id=dataset_version_id,
            status=ExecutionStatus.QUEUED,
            target_model="mock",
            execution_config={},
            total_items=1,
        )
        db.add(execution)
        db.commit()

        print(f"execution_id={execution.id}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
