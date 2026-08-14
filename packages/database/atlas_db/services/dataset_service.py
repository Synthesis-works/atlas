import json
import uuid

from atlas_db.repositories.dataset import DatasetVersionRepository
from atlas_db.repositories.tasks import (
    ConstraintRepository,
    EvaluationRuleRepository,
    PromptRepository,
    TaskRepository,
    TestCaseRepository,
)
from packages.datasets.models import DatasetPack


class DatasetPersistenceService:
    """Service to handle persistence of DatasetPacks to the PostgreSQL database."""

    def __init__(
        self,
        dataset_version_repo: DatasetVersionRepository,
        task_repo: TaskRepository,
        prompt_repo: PromptRepository,
        test_case_repo: TestCaseRepository,
        constraint_repo: ConstraintRepository,
        evaluation_rule_repo: EvaluationRuleRepository,
    ):
        self.dataset_version_repo = dataset_version_repo
        self.task_repo = task_repo
        self.prompt_repo = prompt_repo
        self.test_case_repo = test_case_repo
        self.constraint_repo = constraint_repo
        self.evaluation_rule_repo = evaluation_rule_repo

    def persist_dataset_pack(self, dataset_version_id: uuid.UUID, pack: DatasetPack) -> None:
        """
        Persists a complete DatasetPack by converting its internal Pydantic tasks
        into the database ORM models and grouping them by dataset_version_id.
        """
        db = self.dataset_version_repo.db
        
        try:
            for index, p_task in enumerate(pack.tasks):
                # 1. Create the Task
                task_data = {
                    "dataset_version_id": dataset_version_id,
                    "name": p_task.task_id,
                    "description": p_task.description or p_task.title,
                    "order_index": index,
                    "metadata_": p_task.metadata,
                }
                db_task = self.task_repo.create(obj_in=task_data, commit=False)
                
                # 2. Create the Prompt
                prompt_data = {
                    "task_id": db_task.id,
                    "template": str(p_task.input),
                    "system_instruction": p_task.metadata.get("system_prompt", None)
                }
                self.prompt_repo.create(obj_in=prompt_data, commit=False)
                
                # 3. Create the Main Test Case
                expected_output_val = p_task.expected_output
                tc_data = {
                    "task_id": db_task.id,
                    "input_data": {"input": str(p_task.input)},
                    "expected_output": {"output": expected_output_val} if isinstance(expected_output_val, str) else expected_output_val,
                    "is_hidden": False,
                }
                self.test_case_repo.create(obj_in=tc_data, commit=False)
                
                # 4. Remove Hidden Test Case generation (moved to EvaluationRule)
                # 5. Create Constraints (Time/Memory limits)
                if p_task.constraints:
                    if p_task.constraints.time_limit is not None:
                        self.constraint_repo.create(
                            obj_in={"task_id": db_task.id, "type": "time_limit", "value": str(p_task.constraints.time_limit)}, 
                            commit=False
                        )
                    if p_task.constraints.memory_limit is not None:
                        self.constraint_repo.create(
                            obj_in={"task_id": db_task.id, "type": "memory_limit", "value": str(p_task.constraints.memory_limit)}, 
                            commit=False
                        )
                        
                # 6. Create Evaluation Rule based on tests and configs
                # Base config rule
                if p_task.evaluation:
                    rule_data = {
                        "task_id": db_task.id,
                        "rule_definition": json.dumps(p_task.evaluation.model_dump())
                    }
                    self.evaluation_rule_repo.create(obj_in=rule_data, commit=False)
                
                # Executable evaluation bounds (public/private tests)
                test_context = p_task.metadata.get("test_setup_code")
                if p_task.hidden_tests:
                    hidden_val = p_task.hidden_tests
                    rule_def = hidden_val if isinstance(hidden_val, str) else json.dumps(hidden_val)
                    rule_data_test = {
                        "task_id": db_task.id,
                        "rule_definition": rule_def,
                        "context_setup": test_context,
                        "is_challenge": False,
                    }
                    self.evaluation_rule_repo.create(obj_in=rule_data_test, commit=False)
                
                # Challenge tests
                challenge_tests = p_task.metadata.get("challenge_tests")
                if challenge_tests:
                    c_def = challenge_tests if isinstance(challenge_tests, str) else json.dumps(challenge_tests)
                    c_data = {
                        "task_id": db_task.id,
                        "rule_definition": c_def,
                        "context_setup": test_context,
                        "is_challenge": True,
                    }
                    self.evaluation_rule_repo.create(obj_in=c_data, commit=False)
                    
            db.commit()
            
        except Exception:
            db.rollback()
            raise
