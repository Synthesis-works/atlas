import uuid
import json
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from atlas_db.models.tasks import Task, Prompt, TestCase
from packages.datasets.models import TrainingExample


class DatasetExtractionService:
    """Read-only extraction boundary delivering canonical TrainingExamples for D2."""

    def __init__(self, session: Session):
        self.session = session

    def get_training_examples(self, dataset_version_id: uuid.UUID) -> list[TrainingExample]:
        """
        D2 Extraction Pipeline: Retrieves exactly one TrainingExample per Dataset Task.
        Explicitly enforces 1:1 cardinality for Prompts and canonical TestCases.
        EvaluationRules are structurally partitioned out of this query space.
        """

        # Load tasks bound strictly to the given dataset_version_id, eagerly loading relations
        # to prevent N+1 without invoking Descartes multiplications.
        tasks = (
            self.session.query(Task)
            .options(selectinload(Task.prompts), selectinload(Task.test_cases))
            .filter(Task.dataset_version_id == dataset_version_id)
            .order_by(Task.order_index)  # Ensures deterministic extraction
            .all()
        )

        examples = []
        for task in tasks:
            # 1. Resolve Canonical Prompt (Strict Cardinality)
            if len(task.prompts) == 0:
                raise ValueError(
                    f"Ambiguity/Missing Error: Task {task.id} has no attached Prompts."
                )
            if len(task.prompts) > 1:
                raise ValueError(
                    f"Ambiguity Error: Task {task.id} possesses multiple Prompts; extraction unsafe."
                )
            db_prompt = task.prompts[0]

            # 2. Resolve Canonical Answer (Strict Cardinality)
            # Find the unhidden public test cases
            public_cases = [tc for tc in task.test_cases if not tc.is_hidden]
            if len(public_cases) == 0:
                raise ValueError(
                    f"Ambiguity/Missing Error: Task {task.id} has no public TestCase serving as canonical answer."
                )
            if len(public_cases) > 1:
                raise ValueError(
                    f"Ambiguity Error: Task {task.id} possesses multiple public TestCases; extraction unsafe."
                )
            canonical_tc = public_cases[0]

            # 3. Handle Canonical Output Format Safely
            expected_output = canonical_tc.expected_output

            if isinstance(expected_output, dict) and "output" in expected_output:
                extracted_val = expected_output["output"]
                if isinstance(extracted_val, str):
                    answer_str = extracted_val
                else:
                    answer_str = json.dumps(extracted_val, sort_keys=True)
            elif isinstance(expected_output, str):
                answer_str = expected_output
            else:
                answer_str = json.dumps(expected_output, sort_keys=True)

            # 4. Resolve the training prompt deterministically via existing semantic resolver
            # Replicates template hydration without importing worker dependencies.
            try:
                resolved_prompt = db_prompt.template.format(**canonical_tc.input_data)
            except KeyError as e:
                raise ValueError(f"Missing key in input_data for prompt template: {e}")
            except ValueError as e:
                raise ValueError(f"Invalid format in prompt template: {e}")

            # 5. Hydrate and retain safe structural metadata (e.g. entry_point)
            # Note: No EvaluationRoles are passed/included here.
            raw_metadata = dict(task.metadata_)

            # Explicit fail-closed allowlist restricting dataset metadata payloads natively bounding against silent evaluation leakages.
            ALLOWED_TRAINING_METADATA_KEYS = {"entry_point"}
            metadata = {
                k: v for k, v in raw_metadata.items() if k in ALLOWED_TRAINING_METADATA_KEYS
            }

            example = TrainingExample(
                dataset_version_id=task.dataset_version_id,
                task_id=task.id,
                task_name=task.name,
                prompt=resolved_prompt,
                canonical_answer=answer_str,
                metadata=metadata,
            )
            examples.append(example)

        return examples
