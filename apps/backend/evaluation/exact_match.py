from typing import Any, Dict, Tuple
from .base import BaseEvaluator

class ExactMatchStrategy(BaseEvaluator):
    """
    Evaluates by checking if the prediction exactly matches the reference (after basic string normalization).
    """

    def evaluate(self, reference: Any, prediction: Any) -> Tuple[bool, float, Dict[str, Any]]:
        ref_str = str(reference).strip() if reference is not None else ""
        pred_str = str(prediction).strip() if prediction is not None else ""
        
        passed = (ref_str == pred_str)
        score = 1.0 if passed else 0.0
        
        return passed, score, {
            "strategy": "exact_match",
            "reference_length": len(ref_str),
            "prediction_length": len(pred_str)
        }
