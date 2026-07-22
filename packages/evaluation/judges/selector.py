from .base import BaseJudge
from .exact import ExactMatchJudge
from .numeric import NumericMatchJudge


class JudgeSelector:
    def __init__(self):
        self.judges = {"exact_match": ExactMatchJudge(), "numeric_match": NumericMatchJudge()}

    def get_judge(self, name: str) -> BaseJudge:
        judge = self.judges.get(name)
        if not judge:
            raise ValueError(f"Judge '{name}' not found.")
        return judge
