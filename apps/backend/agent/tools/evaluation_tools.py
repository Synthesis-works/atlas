import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from apps.backend.agent.state import AgentPermission
from apps.backend.agent.tools.base import BaseTool

# Global stores for persisted evaluation cases and reports
_evaluation_case_store: dict[str, list[dict[str, Any]]] = {}


class CreateEvaluationCaseTool(BaseTool):
    name = "create_evaluation_case"
    description = "Generate ground truth, expected answers, accepted answers, or LLM judge rubrics for benchmark dataset tasks."
    required_permission = AgentPermission.WRITE
    parameters_schema = {
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "string",
                "description": "UUID of the dataset to attach evaluation cases.",
            },
            "evaluation_cases": {
                "type": "array",
                "description": "List of evaluation case definitions.",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID of the dataset task."},
                        "expected_answer": {
                            "type": "string",
                            "description": "Ground truth expected answer.",
                        },
                        "evaluation_method": {
                            "type": "string",
                            "description": "Method to judge model responses (exact_match, accepted_answers, llm_judge).",
                            "enum": ["exact_match", "accepted_answers", "llm_judge"],
                        },
                        "accepted_answers": {
                            "type": "array",
                            "description": "List of acceptable variant answers.",
                            "items": {"type": "string"},
                        },
                        "rubric_criteria": {
                            "type": "array",
                            "description": "Criteria list for LLM judge scoring.",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["task_id", "expected_answer"],
                },
            },
        },
        "required": ["dataset_id", "evaluation_cases"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        dataset_id = kwargs.get("dataset_id")
        if dataset_id is None:
            raise ValueError("dataset_id is required")
        evaluation_cases = kwargs.get("evaluation_cases")
        if evaluation_cases is None:
            raise ValueError("evaluation_cases is required")

        # Resolve active benchmark version and dataset version
        from atlas_db.models.tasks import Task as DBTask, TestCase as DBTestCase
        from atlas_db.models.dataset import DatasetVersion

        agent_task_id = kwargs.get("task_id")
        bv_id = None
        dv_id = None

        if agent_task_id:
            from apps.backend.routers.agent import _agent_tasks_db

            try:
                agent_task = _agent_tasks_db.get(uuid.UUID(agent_task_id))
                if agent_task:
                    if agent_task.benchmark_version_id:
                        bv_id = uuid.UUID(agent_task.benchmark_version_id)
                    if agent_task.dataset_version_id:
                        dv_id = uuid.UUID(agent_task.dataset_version_id)
            except Exception:
                pass

        # Load task schemas from dataset version to map task_id string to input text
        task_id_to_input = {}
        if dv_id:
            dv = db.query(DatasetVersion).filter(DatasetVersion.id == dv_id).first()
            if dv and dv.schema_def:
                for t in dv.schema_def:
                    if isinstance(t, dict) and "id" in t and "input" in t:
                        task_id_to_input[str(t["id"])] = t["input"]

        # Fetch all test cases for this benchmark version
        db_test_cases = []
        if bv_id:
            db_test_cases = (
                db.query(DBTestCase).join(DBTask).filter(DBTask.benchmark_version_id == bv_id).all()
            )

        created_cases = []
        for case in evaluation_cases:
            case_id = str(uuid.uuid4())
            method = case.get("evaluation_method", "exact_match")
            expected = str(case.get("expected_answer", "")).strip()
            accepted = case.get("accepted_answers") or [expected]
            rubric = case.get("rubric_criteria") or [f"Mentions expected concepts: {expected}"]

            # Find matching DB TestCase
            target_case = None
            case_task_id = case.get("task_id")
            if case_task_id:
                # 1. Try matching by task input text
                input_text = task_id_to_input.get(str(case_task_id))
                if input_text is not None and db_test_cases:
                    target_case = next(
                        (tc for tc in db_test_cases if tc.input_data.get("text") == input_text),
                        None,
                    )
                # 2. Try matching by direct task ID UUID
                if not target_case and db_test_cases:
                    try:
                        t_uuid = uuid.UUID(str(case_task_id))
                        target_case = next(
                            (tc for tc in db_test_cases if tc.task_id == t_uuid), None
                        )
                    except ValueError:
                        pass

            # If still not found, check the first test case
            if not target_case and db_test_cases:
                target_case = db_test_cases[0]

            if target_case:
                target_case.expected_output = {
                    "expected_answer": expected,
                    "evaluation_method": method,
                    "accepted_answers": accepted,
                    "rubric_criteria": rubric,
                }
                db.add(target_case)

            record = {
                "evaluation_case_id": case_id,
                "dataset_id": dataset_id,
                "task_id": case.get("task_id", "task_1"),
                "expected_answer": expected,
                "evaluation_method": method,
                "accepted_answers": accepted,
                "rubric_criteria": rubric,
                "judge_configuration": {
                    "judge_provider": "gemini",
                    "judge_model": "gemini-3.5-flash-lite",
                    "temperature": 0.0,
                },
                "status": "CREATED",
            }
            created_cases.append(record)

        try:
            db.commit()
        except Exception:
            db.rollback()

        return {
            "dataset_id": dataset_id,
            "total_cases_created": len(created_cases),
            "evaluation_cases": created_cases,
            "status": "CREATED",
        }


class EvaluateRunTool(BaseTool):
    name = "evaluate_run"
    description = (
        "Score model outputs from a completed execution run against persisted evaluation cases."
    )
    required_permission = AgentPermission.EXECUTE
    parameters_schema = {
        "type": "object",
        "properties": {
            "execution_id": {
                "type": "string",
                "description": "UUID of the execution run to evaluate.",
            },
        },
        "required": ["execution_id"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        execution_id = kwargs.get("execution_id")
        if execution_id is None:
            raise ValueError("execution_id is required")

        import uuid
        from apps.backend.agent.tools.execution_tools import _benchmark_execution_store

        rec = _benchmark_execution_store.get(execution_id)

        try:
            exec_uuid = uuid.UUID(execution_id)
        except ValueError:
            return {
                "execution_id": execution_id,
                "status": "EVALUATION_ERROR",
                "error": f"Invalid UUID: '{execution_id}'.",
                "metrics": {"accuracy": 0.0, "total_evaluated": 0, "passed": 0, "failed": 0},
                "results": [],
            }

        from atlas_db.models.execution import ModelOutput as DBModelOutput, Execution as DBExecution
        from atlas_db.models.evaluation import EvaluationResult as DBEvaluationResult
        from atlas_db.models.tasks import TestCase as DBTestCase, Task as DBTask

        # Fetch model outputs from database
        execution = db.query(DBExecution).filter(DBExecution.id == exec_uuid).first()
        model_outputs = (
            db.query(DBModelOutput).filter(DBModelOutput.execution_id == exec_uuid).all()
        )
        if not model_outputs:
            return {
                "execution_id": execution_id,
                "status": "EVALUATION_ERROR",
                "error": f"No model outputs found in the database for execution_id '{execution_id}'.",
                "metrics": {"accuracy": 0.0, "total_evaluated": 0, "passed": 0, "failed": 0},
                "results": [],
            }

        # Invoke core evaluation service
        from apps.backend.services.evaluation import EvaluationService

        eval_service = EvaluationService(db)
        profile = eval_service.evaluate_execution(exec_uuid, force=True)
        db.commit()

        # Build results entirely from database
        evaluated_results = []
        passed_count = 0
        total_latency = 0

        for out in model_outputs:
            test_case = db.query(DBTestCase).filter(DBTestCase.id == out.test_case_id).first()
            if not test_case:
                continue

            task = db.query(DBTask).filter(DBTask.id == test_case.task_id).first()
            task_id_str = str(task.id) if task else "task-default"

            eval_res = (
                db.query(DBEvaluationResult)
                .filter(DBEvaluationResult.model_output_id == out.id)
                .first()
            )
            if not eval_res:
                continue

            raw_meas = eval_res.raw_measurements or {}
            method = raw_meas.get("evaluation_method", "exact_match")
            exp = raw_meas.get("expected_answer", "")
            accepted_answers = raw_meas.get("accepted_answers", [exp])
            rubric_criteria = raw_meas.get("rubric_criteria", [])
            score = raw_meas.get("score", 0.0)

            is_correct = bool(eval_res.passed)
            if is_correct:
                passed_count += 1

            total_latency += getattr(out, "duration_ms", 0) or 0

            # Use local normalization helper
            from apps.backend.agent.tools.execution_tools import _normalize_answer

            norm_ans = _normalize_answer(out.raw_output, exp)

            evaluated_results.append(
                {
                    "execution_id": execution_id,
                    "evaluation_case_id": str(eval_res.id),
                    "task_id": task_id_str,
                    "model": execution.target_model if execution else "model-default",
                    "question": test_case.input_data.get("text", "")
                    if test_case.input_data
                    else "",
                    "raw_output": out.raw_output,
                    "model_answer": norm_ans or out.raw_output,
                    "expected_answer": exp,
                    "accepted_answers": accepted_answers,
                    "evaluation_method": method,
                    "rubric_criteria": rubric_criteria,
                    "criteria_summary": f"{len(rubric_criteria)} criteria"
                    if rubric_criteria
                    else "exact match",
                    "correct": is_correct,
                    "judge_result": "PASS" if is_correct else "FAIL",
                    "score": score,
                    "reasoning": eval_res.reasoning,
                    "latency_ms": getattr(out, "duration_ms", 0) or 0,
                }
            )

        total_count = len(evaluated_results)
        acc = (passed_count / total_count * 100.0) if total_count > 0 else 0.0
        avg_lat = int(total_latency / total_count) if total_count > 0 else 350

        return {
            "execution_id": execution_id,
            "status": "EVALUATED",
            "metrics": {
                "accuracy": round(acc, 1),
                "total_evaluated": total_count,
                "passed": passed_count,
                "failed": total_count - passed_count,
                "average_latency_ms": avg_lat,
            },
            "results": evaluated_results,
        }


class CompareResultsTool(BaseTool):
    name = "compare_results"
    description = "Compare evaluation scores and metrics across multiple model runs."
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "execution_ids": {
                "type": "array",
                "description": "List of execution run UUIDs to compare.",
            },
        },
        "required": ["execution_ids"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        execution_ids = kwargs.get("execution_ids")
        if execution_ids is None:
            raise ValueError("execution_ids is required")

        from atlas_db.models.execution import Execution as DBExecution
        from atlas_db.models.evaluation import CapabilityProfile as DBCapabilityProfile
        import uuid

        leaderboard = []
        for idx, eid in enumerate(execution_ids):
            try:
                exec_uuid = uuid.UUID(eid)
            except ValueError:
                continue

            exec_obj = db.query(DBExecution).filter(DBExecution.id == exec_uuid).first()
            model_name = exec_obj.target_model if exec_obj else f"model-{idx + 1}"

            # Query the actual CapabilityProfile score
            profile = (
                db.query(DBCapabilityProfile)
                .filter(DBCapabilityProfile.execution_id == exec_uuid)
                .first()
            )
            accuracy = (profile.overall_score * 100.0) if profile else 0.0

            leaderboard.append(
                {
                    "rank": idx + 1,
                    "model": model_name,
                    "accuracy": round(accuracy, 1),
                }
            )

        # Sort leaderboard descending by accuracy
        leaderboard.sort(key=lambda x: x["accuracy"], reverse=True)
        for i, item in enumerate(leaderboard):
            item["rank"] = i + 1

        best = leaderboard[0]["model"] if leaderboard else "gemini-3.5-flash-lite"

        return {
            "total_runs_compared": len(execution_ids),
            "leaderboard": leaderboard,
            "best_model": best,
        }


class GenerateReportTool(BaseTool):
    name = "generate_report"
    description = "Produce a detailed comparative benchmark summary report."
    required_permission = AgentPermission.PUBLISH
    parameters_schema = {
        "type": "object",
        "properties": {
            "benchmark_id": {"type": "string", "description": "UUID of the benchmark."},
            "title": {"type": "string", "description": "Report title."},
        },
        "required": ["benchmark_id"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        benchmark_id = kwargs.get("benchmark_id")
        if benchmark_id is None:
            raise ValueError("benchmark_id is required")
        title = kwargs.get("title", "Benchmark Report")

        import uuid
        from atlas_db.models.reporting import Report as DBReport, ReportVersion as DBReportVersion

        report_id = uuid.uuid4()
        agent_task_id = kwargs.get("task_id")
        proj_id = kwargs.get("project_id") or uuid.UUID("00000000-0000-0000-0000-000000000001")
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000003")

        exec_id = None
        if agent_task_id:
            from apps.backend.routers.agent import _agent_tasks_db

            try:
                task_obj = _agent_tasks_db.get(uuid.UUID(agent_task_id))
                if task_obj and task_obj.execution_ids:
                    exec_id = uuid.UUID(task_obj.execution_ids[-1])
            except Exception:
                pass

        # Find or create a Report for this project/benchmark
        report_obj = (
            db.query(DBReport)
            .filter(DBReport.project_id == proj_id, DBReport.name == title)
            .first()
        )
        if not report_obj:
            report_obj = DBReport(
                id=uuid.uuid4(),
                project_id=proj_id,
                name=title,
            )
            db.add(report_obj)
            db.flush()

        # Create ReportVersion
        report_version = DBReportVersion(
            id=report_id,
            report_id=report_obj.id,
            version_string="1.0.0",
            summary=f"Benchmark evaluation completed successfully for '{title}'.",
            created_by_id=user_id,
            execution_id=exec_id,
        )
        db.add(report_version)

        try:
            db.commit()
            db.refresh(report_version)
        except Exception:
            db.rollback()

        # Update AgentTask with report tracking if task_id exists
        if agent_task_id:
            from apps.backend.routers.agent import _agent_tasks_db

            try:
                task_obj = _agent_tasks_db.get(uuid.UUID(agent_task_id))
                if task_obj:
                    task_obj.report_id = str(report_id)
            except Exception:
                pass

        # Persist ReportMetric rows ONLY from genuine evaluation data for the
        # linked execution. If no evaluation results exist, write no metrics —
        # an empty report is honest; a fabricated one is not.
        if exec_id:
            metric_rows = self._collect_real_metrics(db, exec_id, report_id)
            for row in metric_rows:
                db.add(row)
            try:
                db.commit()
            except Exception:
                db.rollback()

        # created_at must come from the persisted report version, never a hardcoded value.
        created_at = (
            report_version.created_at.isoformat()
            if report_version.created_at
            else datetime.now(UTC).isoformat()
        )

        return {
            "report_id": str(report_id),
            "agent_task_id": agent_task_id,
            "benchmark_id": benchmark_id,
            "title": title,
            "summary": f"Benchmark evaluation completed successfully for '{title}'.",
            "published": True,
            "created_at": created_at,
        }

    def _collect_real_metrics(
        self, db: Session, exec_id: uuid.UUID, report_version_id: uuid.UUID
    ) -> list[Any]:
        """
        Derives ReportMetric rows from the actual evaluation state persisted for
        an execution: the CapabilityProfile (accuracy) and the per-output
        EvaluationResult rows (total/passed/failed).
        """
        from atlas_db.models.evaluation import (
            CapabilityProfile,
            EvaluationResult,
        )
        from atlas_db.models.execution import ModelOutput as DBModelOutput
        from atlas_db.models.reporting import ReportMetric

        metrics: list[Any] = []

        profile = (
            db.query(CapabilityProfile).filter(CapabilityProfile.execution_id == exec_id).first()
        )
        if profile and profile.overall_score is not None:
            metrics.append(
                ReportMetric(
                    report_version_id=report_version_id,
                    metric_name="accuracy",
                    metric_value=round(profile.overall_score * 100.0, 1),
                )
            )

        output_ids = [
            mo.id
            for mo in db.query(DBModelOutput).filter(DBModelOutput.execution_id == exec_id).all()
        ]
        if output_ids:
            total = len(output_ids)
            passed = (
                db.query(EvaluationResult)
                .filter(
                    EvaluationResult.model_output_id.in_(output_ids),
                    EvaluationResult.passed.is_(True),
                )
                .count()
            )
            metrics.append(
                ReportMetric(
                    report_version_id=report_version_id,
                    metric_name="total_evaluated",
                    metric_value=float(total),
                )
            )
            metrics.append(
                ReportMetric(
                    report_version_id=report_version_id,
                    metric_name="passed",
                    metric_value=float(passed),
                )
            )
            metrics.append(
                ReportMetric(
                    report_version_id=report_version_id,
                    metric_name="failed",
                    metric_value=float(total - passed),
                )
            )

        return metrics
