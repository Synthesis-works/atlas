from .base import BaseJudge


class NumericMatchJudge(BaseJudge):
    def evaluate(self, expected: str, actual: str) -> tuple[bool, float, float]:
        try:
            # Simple float comparison
            expected_val = float(expected)
            actual_val = float(actual)
            passed = expected_val == actual_val
            return passed, 1.0 if passed else 0.0, 1.0
        except ValueError:
            return False, 0.0, 1.0
