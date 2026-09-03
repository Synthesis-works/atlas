import uuid
from collections.abc import Sequence

from atlas_db.models.dataset import Dataset, DatasetLifecycle, DatasetStatus, DatasetVersion
from atlas_db.models.tasks import Prompt, Task, TestCase
from atlas_db.repositories.dataset import DatasetRepository, DatasetVersionRepository
from atlas_db.repositories.tasks import PromptRepository, TaskRepository, TestCaseRepository
from sqlalchemy import select

from apps.backend.schemas.datasets import (
    DatasetCreate,
    DatasetRead,
    DatasetTaskUpload,
    DatasetUpdate,
    DatasetValidationResult,
)


class DatasetService:
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        version_repo: DatasetVersionRepository,
        task_repo: TaskRepository,
        prompt_repo: PromptRepository,
        test_case_repo: TestCaseRepository,
    ):
        self.dataset_repo = dataset_repo
        self.version_repo = version_repo
        self.task_repo = task_repo
        self.prompt_repo = prompt_repo
        self.test_case_repo = test_case_repo

    @property
    def session(self):
        return self.dataset_repo.db

    def get_dataset(self, dataset_id: uuid.UUID) -> Dataset | None:
        dataset = self.dataset_repo.get(dataset_id)
        if dataset and dataset.status == DatasetStatus.ARCHIVED:
            return None
        return dataset

    def list_datasets(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Dataset]:
        stmt = (
            select(Dataset)
            .where(Dataset.project_id == project_id, Dataset.status != DatasetStatus.ARCHIVED)
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def _to_read(
        self, dataset: Dataset, versions: list[DatasetVersion] | None = None
    ) -> DatasetRead:
        version = versions[-1] if versions else self._latest_version(dataset.id)
        tasks = self._tasks_for_version(version.id) if version else []

        sample_tasks: list[dict] = []
        for task in tasks:
            for tc in self.test_case_repo.list(task_id=task.id):
                sample_tasks.append(
                    {
                        "name": task.name,
                        "description": task.description,
                        "input": tc.input_data,
                        "expected_output": tc.expected_output,
                    }
                )

        return DatasetRead(
            id=dataset.id,
            project_id=dataset.project_id,
            created_by_member_id=dataset.created_by_member_id,
            status=dataset.status,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            name=dataset.name,
            description=dataset.description,
            registry_id=dataset.registry_id,
            source_id=dataset.source_id,
            license_id=dataset.license_id,
            total_tasks=len(tasks),
            sample_tasks=sample_tasks,
            versions=versions if versions is not None else self._versions(dataset.id),
        )

    def create_dataset(
        self, project_id: uuid.UUID, member_id: uuid.UUID, data: DatasetCreate
    ) -> DatasetRead:
        dataset = Dataset(
            project_id=project_id,
            created_by_member_id=member_id,
            status=DatasetStatus.ACTIVE,
            name=data.name,
            description=data.description,
            registry_id=data.registry_id,
            source_id=data.source_id,
            license_id=data.license_id,
        )
        self.dataset_repo.create(dataset, commit=False)
        self.session.flush()

        if data.tasks:
            version = DatasetVersion(
                dataset_id=dataset.id,
                version_string=data.version_string,
                storage_path=f"datasets/{dataset.id}/{data.version_string}",
                lifecycle=DatasetLifecycle.UPLOADED,
                created_by_id=member_id,
            )
            self.version_repo.create(version, commit=False)
            self.session.flush()
            self._seed_tasks(dataset=dataset, version=version, member_id=member_id, tasks=data.tasks)

        self.session.commit()
        self.session.refresh(dataset)
        return self._to_read(dataset)

    def update_dataset(
        self, dataset_id: uuid.UUID, project_id: uuid.UUID, data: DatasetUpdate
    ) -> DatasetRead | None:
        dataset = self.get_dataset(dataset_id)
        if not dataset or dataset.project_id != project_id:
            return None
        updates = data.model_dump(exclude_none=True)
        updated = self.dataset_repo.update(db_obj=dataset, obj_in=updates)
        return self._to_read(updated)

    def upload_tasks(
        self,
        dataset_id: uuid.UUID,
        project_id: uuid.UUID,
        member_id: uuid.UUID,
        upload: DatasetTaskUpload,
    ) -> DatasetVersion | None:
        dataset = self.get_dataset(dataset_id)
        if not dataset or dataset.project_id != project_id:
            return None

        version = DatasetVersion(
            dataset_id=dataset_id,
            version_string=upload.version_string,
            storage_path=f"datasets/{dataset_id}/{upload.version_string}",
            lifecycle=DatasetLifecycle.UPLOADED,
            created_by_id=member_id,
        )
        self.version_repo.create(version, commit=False)
        self.session.flush()
        self._seed_tasks(dataset=dataset, version=version, member_id=member_id, tasks=upload.tasks)
        self.session.commit()
        return version

    def validate_dataset(
        self, dataset_id: uuid.UUID, project_id: uuid.UUID
    ) -> DatasetValidationResult | None:
        dataset = self.get_dataset(dataset_id)
        if not dataset or dataset.project_id != project_id:
            return None

        version = self._latest_version(dataset_id)
        if version is None:
            return DatasetValidationResult(
                dataset_id=dataset_id,
                lifecycle=DatasetLifecycle.FAILED,
                valid=False,
                messages=["Dataset has no version to validate."],
            )

        tasks = self._tasks_for_version(version.id)
        messages: list[str] = []
        valid = True
        if not tasks:
            valid = False
            messages.append("Dataset version has no tasks.")

        sample = None
        for task in tasks:
            test_cases = self.test_case_repo.list(task_id=task.id)
            if not test_cases:
                valid = False
                messages.append(f"Task '{task.name}' has no test cases.")
            if sample is None and test_cases:
                sample = test_cases[0]

        version.lifecycle = DatasetLifecycle.VALID if valid else DatasetLifecycle.FAILED
        self.session.commit()

        if valid:
            messages.append("Dataset schema is valid.")
        else:
            messages.append("Dataset schema validation failed.")

        return DatasetValidationResult(
            dataset_id=dataset_id,
            version_id=version.id,
            lifecycle=version.lifecycle,
            valid=valid,
            task_count=len(tasks),
            messages=messages,
        )

    def get_dataset_details(self, dataset_id: uuid.UUID) -> DatasetRead | None:
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return None
        return self._to_read(dataset)

    def _seed_tasks(self, dataset, version, member_id, tasks) -> None:
        for idx, item in enumerate(tasks):
            task = Task(
                id=uuid.uuid4(),
                dataset_version_id=version.id,
                name=f"task_{idx}",
                description=item.description or f"Task item {idx}",
                order_index=idx,
                created_by_id=member_id,
            )
            self.task_repo.create(task, commit=False)
            self.session.flush()
            self.prompt_repo.create(
                Prompt(id=uuid.uuid4(), task_id=task.id, template="{input}"), commit=False
            )
            self.test_case_repo.create(
                TestCase(
                    id=uuid.uuid4(),
                    task_id=task.id,
                    dataset_version_id=version.id,
                    input_data=item.input,
                    expected_output=item.expected_output,
                ),
                commit=False,
            )

    def _versions(self, dataset_id: uuid.UUID) -> list[DatasetVersion]:
        stmt = select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id)
        return list(self.session.execute(stmt).scalars().all())

    def _latest_version(self, dataset_id: uuid.UUID) -> DatasetVersion | None:
        versions = self._versions(dataset_id)
        if not versions:
            return None
        return max(versions, key=lambda v: v.created_at.replace(tzinfo=None))

    def _tasks_for_version(self, version_id: uuid.UUID) -> list[Task]:
        stmt = select(Task).where(Task.dataset_version_id == version_id)
        return list(self.session.execute(stmt).scalars().all())
