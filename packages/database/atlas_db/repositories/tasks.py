from atlas_db.models.tasks import Constraint, EvaluationRule, Prompt, Task, TestCase

from .base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task


class PromptRepository(BaseRepository[Prompt]):
    model = Prompt


class TestCaseRepository(BaseRepository[TestCase]):
    model = TestCase


class ConstraintRepository(BaseRepository[Constraint]):
    model = Constraint


class EvaluationRuleRepository(BaseRepository[EvaluationRule]):
    model = EvaluationRule
