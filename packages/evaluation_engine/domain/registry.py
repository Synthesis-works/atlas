from typing import Dict, Any, Type, Tuple, Optional
from packages.evaluation_engine.domain.evaluator import BaseEvaluator
from packages.evaluation_engine.domain.scoring import BaseScoringStrategy
from packages.evaluation_engine.domain.judge import BaseJudgeAdapter

class EvaluationRegistry:
    """
    Composition root for the Evaluation Engine.
    Maps benchmark types / evaluation strategies to the appropriate pipeline components.
    """
    def __init__(self):
        self._registry: Dict[str, Tuple[Type[BaseEvaluator], Type[BaseScoringStrategy], Optional[Type[BaseJudgeAdapter]]]] = {}

    def register(self, strategy_type: str, evaluator: Type[BaseEvaluator], scoring: Type[BaseScoringStrategy], judge: Optional[Type[BaseJudgeAdapter]] = None):
        self._registry[strategy_type] = (evaluator, scoring, judge)

    def resolve(self, strategy_type: str) -> Tuple[BaseEvaluator, BaseScoringStrategy, Optional[BaseJudgeAdapter]]:
        if strategy_type not in self._registry:
            raise ValueError(f"No evaluation pipeline registered for strategy_type: {strategy_type}")
        
        evaluator_cls, scoring_cls, judge_cls = self._registry[strategy_type]
        judge_instance = judge_cls() if judge_cls else None
        
        # If the evaluator needs a judge, we would typically inject it here via init
        # For simplicity in this interface, we assume evaluators that need a judge
        # accept it in their constructor.
        if judge_instance:
            evaluator_instance = evaluator_cls(judge=judge_instance)
        else:
            evaluator_instance = evaluator_cls()
            
        scoring_instance = scoring_cls()
        
        return evaluator_instance, scoring_instance, judge_instance
