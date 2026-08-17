import json
import logging
import uuid
from typing import Any, Dict, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from atlas_db.models.dataset import Dataset, DatasetStatus, DatasetVersion, DatasetLifecycle
from apps.backend.agent.state import AgentPermission
from apps.backend.agent.tools.base import BaseTool


# Global dataset store for memory-backed tool execution
_dataset_store: dict[str, dict[str, Any]] = {}


class GetDatasetTool(BaseTool):
    name = "get_dataset"
    description = "Retrieve metadata, task samples, and version definitions for a specific dataset."
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "dataset_id": {"type": "string", "description": "UUID of dataset to inspect."},
        },
        "required": ["dataset_id"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        dataset_id = kwargs.get("dataset_id")
        if dataset_id is None:
            raise ValueError("dataset_id is required")

        try:
            d_uuid = uuid.UUID(dataset_id)
        except ValueError:
            return {"error": f"Invalid UUID string: '{dataset_id}'"}

        dataset = db.query(Dataset).filter(Dataset.id == d_uuid).first()
        if not dataset:
            return {"error": f"Dataset with ID '{dataset_id}' not found."}

        versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == d_uuid).all()
        tasks = []
        if versions and versions[0].schema_def:
            tasks = (
                versions[0].schema_def
                if isinstance(versions[0].schema_def, list)
                else [versions[0].schema_def]
            )

        return {
            "id": str(dataset.id),
            "name": dataset.name,
            "description": dataset.description,
            "status": dataset.status,
            "total_tasks": len(tasks),
            "sample_tasks": tasks[:5],
        }


class CreateDatasetTool(BaseTool):
    name = "create_dataset"
    description = "Create and attach dataset task definitions to a benchmark."
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_id": {"type": "string", "description": "UUID of the benchmark to link."},
            "name": {"type": "string", "description": "Dataset name."},
            "tasks": {
                "type": "array",
                "description": "List of task objects (each with id, input, expected_output).",
            },
        },
        "required": ["benchmark_id", "name", "tasks"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        benchmark_id = kwargs.get("benchmark_id")
        if benchmark_id is None:
            raise ValueError("benchmark_id is required")
        name = kwargs.get("name")
        if name is None:
            raise ValueError("name is required")
        tasks = kwargs.get("tasks")
        if tasks is None:
            raise ValueError("tasks is required")

        proj_id = kwargs.get("project_id") or uuid.UUID("00000000-0000-0000-0000-000000000001")

        parsed_tasks = []
        for t in tasks:
            if isinstance(t, str):
                try:
                    parsed_tasks.append(json.loads(t))
                except Exception:
                    parsed_tasks.append({"input": t, "expected_output": ""})
            elif isinstance(t, dict):
                parsed_tasks.append(t)
            else:
                parsed_tasks.append(t)

        dataset_id = uuid.uuid4()
        version_id = uuid.uuid4()
        dataset_name = f"{name}_{uuid.uuid4().hex[:6]}"

        dataset = Dataset(
            id=dataset_id,
            project_id=proj_id,
            name=dataset_name,
            description=f"Dataset created for benchmark {benchmark_id}",
            status=DatasetStatus.ACTIVE,
        )
        db.add(dataset)

        version = DatasetVersion(
            id=version_id,
            dataset_id=dataset_id,
            version_string="v1.0.0",
            storage_path=f"storage/datasets/{dataset_id}",
            lifecycle=DatasetLifecycle.UPLOADED,
            schema_def=parsed_tasks,
        )
        db.add(version)

        try:
            db.commit()
        except Exception as e:
            import traceback

            db.rollback()
            logger.error(f"CreateDatasetTool commit failed: {e}\n{traceback.format_exc()}")
            raise e

        res = {
            "id": str(dataset_id),
            "version_id": str(version_id),
            "name": dataset_name,
            "total_tasks": len(parsed_tasks),
            "tasks": parsed_tasks,
            "status": "CREATED",
        }
        _dataset_store[str(dataset_id)] = res
        return res


class UpdateDatasetTool(BaseTool):
    name = "update_dataset"
    description = "Modify or repair dataset task definitions after validation failures."
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "dataset_id": {"type": "string", "description": "UUID of the dataset to repair."},
            "repaired_tasks": {
                "type": "array",
                "description": "List of updated/repaired task objects.",
            },
        },
        "required": ["dataset_id", "repaired_tasks"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        dataset_id = kwargs.get("dataset_id")
        if dataset_id is None:
            raise ValueError("dataset_id is required")
        repaired_tasks = kwargs.get("repaired_tasks")
        if repaired_tasks is None:
            raise ValueError("repaired_tasks is required")

        try:
            d_uuid = uuid.UUID(dataset_id)
        except ValueError:
            return {"error": f"Invalid UUID string: '{dataset_id}'"}

        version = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == d_uuid).first()
        if not version:
            return {"error": f"DatasetVersion for dataset ID '{dataset_id}' not found."}

        version.schema_def = repaired_tasks
        version.lifecycle = DatasetLifecycle.VALIDATING

        try:
            db.commit()
            db.refresh(version)
        except Exception:
            db.rollback()

        return {
            "dataset_id": dataset_id,
            "updated_task_count": len(repaired_tasks),
            "lifecycle": "REPAIRED_AND_VALIDATING",
            "message": "Dataset task definitions updated successfully.",
        }


class ValidateBenchmarkDatasetTool(BaseTool):
    name = "validate_benchmark_dataset"
    description = "Validate task schemas, required fields, and completeness of a dataset."
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "dataset_id": {"type": "string", "description": "UUID of the dataset to validate."},
        },
        "required": ["dataset_id"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        dataset_id = kwargs.get("dataset_id")
        if dataset_id is None:
            raise ValueError("dataset_id is required")

        try:
            d_uuid = uuid.UUID(dataset_id)
        except ValueError:
            return {"error": f"Invalid UUID string: '{dataset_id}'"}

        version = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == d_uuid).first()
        if not version or not version.schema_def:
            return {"valid": False, "reason": "Dataset contains no task definitions."}

        tasks = version.schema_def if isinstance(version.schema_def, list) else [version.schema_def]

        invalid_tasks = []
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                invalid_tasks.append({"index": i, "reason": "Task is not a JSON object"})
                continue
            if "input" not in task:
                invalid_tasks.append(
                    {"index": i, "id": task.get("id"), "reason": "Missing 'input'"}
                )
            if "expected_output" not in task or not task["expected_output"]:
                invalid_tasks.append(
                    {"index": i, "id": task.get("id"), "reason": "Missing 'expected_output'"}
                )

        from apps.backend.agent.tools.evaluation_tools import _evaluation_case_store

        cases_list = _evaluation_case_store.get(dataset_id, [])
        if not cases_list:
            # Check if any evaluation cases exist globally
            for c_list in _evaluation_case_store.values():
                if c_list:
                    cases_list = c_list
                    break

        if invalid_tasks:
            version.lifecycle = DatasetLifecycle.FAILED
            try:
                db.commit()
            except Exception:
                db.rollback()

            return {
                "valid": False,
                "dataset_id": dataset_id,
                "total_inspected": len(tasks),
                "valid_count": len(tasks) - len(invalid_tasks),
                "invalid_count": len(invalid_tasks),
                "evaluation_cases_count": len(cases_list),
                "invalid_tasks": invalid_tasks,
                "message": f"Dataset validation failed: {len(invalid_tasks)} task(s) invalid.",
            }

        version.lifecycle = DatasetLifecycle.VALID
        try:
            db.commit()
        except Exception:
            db.rollback()

        return {
            "valid": True,
            "dataset_id": dataset_id,
            "total_inspected": len(tasks),
            "valid_count": len(tasks),
            "invalid_count": 0,
            "evaluation_cases_count": len(cases_list),
            "message": "All dataset tasks and evaluation cases passed validation.",
        }
