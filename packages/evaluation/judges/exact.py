from .base import BaseJudge


class ExactMatchJudge(BaseJudge):
    def evaluate(self, expected: str, actual: str) -> tuple[bool, float, float]:
        # Perform strict string equality
        passed = str(expected).strip() == str(actual).strip()
        score = 1.0 if passed else 0.0
        confidence = 1.0  # Deterministic judge has full confidence
        return passed, score, confidence
