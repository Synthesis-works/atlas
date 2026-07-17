from .base import BaseRepository
from atlas_db.models.tasks import Task, Prompt, TestCase, Constraint, EvaluationRule

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
