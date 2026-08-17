import os
import re
import time
import uuid
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from atlas_db.models.execution import Execution, ExecutionStatus
from apps.backend.agent.state import AgentPermission
from apps.backend.agent.tools.base import BaseTool
from packages.llm.clients.gemini import GeminiClient
from packages.llm.clients.grok import GrokClient
from packages.llm.clients.mistral import MistralClient
from packages.llm.models.prompt import Prompt

# Centralized model registry holds available target configurations


def get_configured_models() -> dict[str, Any]:
    """Inspects environment keys to return available vs unavailable LLM models."""
    from packages.llm.registry import ModelRegistry

    all_models = ModelRegistry.get_all_models()
    available = [m for m in all_models if m["available"]]
    unavailable = [m for m in all_models if not m["available"]]
    return {
        "available_models": available,
        "unavailable_models": unavailable,
    }


class GetAvailableModelsTool(BaseTool):
    name = "get_available_models"
    description = (
        "Check which LLM models are currently available and configured with valid API credentials."
    )
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {},
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:

        return get_configured_models()


def _normalize_answer(raw_text: str, expected: str) -> str:
    """Extracts concise normalized answer from raw LLM text response."""
    text = raw_text.strip()
    if not text:
        return ""

    exp_clean = expected.strip().lower()

    # Check if expected appears cleanly in response
    if exp_clean and exp_clean in text.lower():
        return expected.strip()

    # Extract numbers if expected is numeric
    if exp_clean.isdigit():
        numbers = re.findall(r"\b\d+\b", text)
        if numbers:
            return numbers[0]

    # Clean markdown formatting and return first meaningful non-empty line
    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip() and not line.strip().startswith("**")
    ]
    if lines:
        return lines[0][:120]
    return text[:120]


class RunBenchmarkTool(BaseTool):
    name = "run_benchmark"
    description = "Dispatch execution run(s) for a benchmark against one or more target LLM models."
    required_permission = AgentPermission.EXECUTE
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_version_id": {
                "type": "string",
                "description": "UUID of the benchmark version to run.",
            },
            "dataset_version_id": {
                "type": "string",
                "description": "UUID of the dataset version to run.",
            },
            "target_models": {
                "type": "array",
                "description": "List of model identifiers to test (e.g. ['gemini-3.5-flash-lite', 'grok-2-latest']).",
            },
        },
        "required": ["benchmark_version_id", "dataset_version_id", "target_models"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        benchmark_version_id = kwargs.get("benchmark_version_id")
        if benchmark_version_id is None:
            raise ValueError("benchmark_version_id is required")
        dataset_version_id = kwargs.get("dataset_version_id")
        if dataset_version_id is None:
            raise ValueError("dataset_version_id is required")
        target_models = kwargs.get("target_models")
        if target_models is None:
            raise ValueError("target_models is required")
        try:
            bv_uuid = uuid.UUID(benchmark_version_id)
            dv_uuid = uuid.UUID(dataset_version_id)
        except ValueError:
            raise ValueError("Invalid benchmark_version_id or dataset_version_id UUID")

        proj_id = kwargs.get("project_id") or uuid.UUID("00000000-0000-0000-0000-000000000001")
        agent_task_id = kwargs.get("task_id")
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000003")

        # Validate that selected models are configured/available in our registry
        from packages.llm.registry import ModelRegistry

        all_models = ModelRegistry.get_all_models()
        available_model_names = {m["model"] for m in all_models if m["available"]}
        available_identifiers = {
            f"{m['provider']}/{m['model']}" for m in all_models if m["available"]
        }

        for model in target_models:
            if model not in available_model_names and model not in available_identifiers:
                raise ValueError(
                    f"Model '{model}' is not configured/available. Please configure API credentials or host connection."
                )

        # Instantiate core ExecutionApplicationService
        from packages.execution_engine.application.execution_app_service import (
            ExecutionApplicationService,
        )
        from packages.execution_engine.domain.services import ExecutionService
        from packages.execution_engine.persistence.repository import SqlAlchemyExecutionRepository
        from atlas_db.repositories.authoring import BenchmarkRepository

        domain_service = ExecutionService()
        execution_repo = SqlAlchemyExecutionRepository(db)
        benchmark_repo = BenchmarkRepository(db)
        service = ExecutionApplicationService(domain_service, execution_repo, benchmark_repo)

        created_ids = []
        for model in target_models:
            execution = service.submit_execution(
                benchmark_version_id=bv_uuid,
                dataset_version_id=dv_uuid,
                submitted_by=user_id,
                target_model=model,
            )
            created_ids.append(str(execution.id))

        # Commit transaction so worker or synchronous eager task can query the records
        try:
            db.commit()
        except Exception:
            db.rollback()

        # Update AgentTask with execution tracking
        if agent_task_id:
            from apps.backend.routers.agent import _agent_tasks_db

            try:
                task_obj = _agent_tasks_db.get(uuid.UUID(agent_task_id))
                if task_obj:
                    if not hasattr(task_obj, "execution_ids") or not task_obj.execution_ids:
                        task_obj.execution_ids = []
                    for eid in created_ids:
                        if eid not in task_obj.execution_ids:
                            task_obj.execution_ids.append(eid)
            except Exception:
                pass

        return {
            "benchmark_version_id": benchmark_version_id,
            "execution_ids": created_ids,
            "models_dispatched": target_models,
            "status": "DISPATCHED",
            "message": f"Successfully submitted executions for {len(target_models)} models via core execution service.",
        }


class GetRunStatusTool(BaseTool):
    name = "get_run_status"
    description = "Check status, progress, and output summary of a queued or running execution."
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "execution_id": {"type": "string", "description": "UUID of execution to inspect."},
        },
        "required": ["execution_id"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        execution_id = kwargs.get("execution_id")
        if execution_id is None:
            raise ValueError("execution_id is required")

        try:
            exec_uuid = uuid.UUID(execution_id)
        except ValueError:
            return {
                "execution_id": execution_id,
                "status": "FAILED",
                "error": f"Invalid UUID: '{execution_id}'",
                "progress": "0%",
            }

        from atlas_db.models.execution import Execution as DBExecution

        exec_obj = db.query(DBExecution).filter(DBExecution.id == exec_uuid).first()
        if not exec_obj:
            from packages.execution_engine.persistence.models import ExecutionModel

            exec_obj = db.query(ExecutionModel).filter(ExecutionModel.id == exec_uuid).first()

        if not exec_obj:
            return {
                "execution_id": execution_id,
                "status": "FAILED",
                "error": f"Execution {execution_id} not found in database.",
                "progress": "0%",
            }

        # Normalize status string from enum or raw text
        status_val = str(exec_obj.status).split(".")[-1]
        total = getattr(exec_obj, "total_items", 0) or 0
        completed = getattr(exec_obj, "completed_items", 0) or 0
        progress_pct = f"{int((completed / total) * 100)}%" if total > 0 else "0%"

        return {
            "execution_id": execution_id,
            "status": status_val,
            "progress": progress_pct,
            "completed_items": completed,
            "total_items": total,
        }
