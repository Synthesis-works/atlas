import uuid
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from atlas_db.models.execution import ExecutionStatus
from atlas_db.models.evaluation import EvaluationStrategy, StrategyType, EvaluationStrategyVersion, EvaluationResult, CapabilityProfile
from atlas_db.repositories.execution import ExecutionRepository, ModelOutputRepository
from atlas_db.repositories.evaluation import EvaluationStrategyRepository, EvaluationStrategyVersionRepository, EvaluationResultRepository, CapabilityProfileRepository, CapabilityScoreRepository
from atlas_db.repositories.tasks import TestCaseRepository
from apps.backend.evaluation import ExactMatchStrategy

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self, db: Session):
        self.db = db
        self.execution_repo = ExecutionRepository(db)
        self.model_output_repo = ModelOutputRepository(db)
        self.test_case_repo = TestCaseRepository(db)
        self.strategy_repo = EvaluationStrategyRepository(db)
        self.strategy_version_repo = EvaluationStrategyVersionRepository(db)
        self.eval_result_repo = EvaluationResultRepository(db)
        self.cap_profile_repo = CapabilityProfileRepository(db)
        self.cap_score_repo = CapabilityScoreRepository(db)
        
        self.exact_match = ExactMatchStrategy()

    def _get_or_create_strategy_version(self) -> EvaluationStrategyVersion:
        strategy = self.strategy_repo.get_by(type=StrategyType.EXACT_MATCH)
        if not strategy:
            strategy = self.strategy_repo.create(
                EvaluationStrategy(
                    name="System Exact Match",
                    type=StrategyType.EXACT_MATCH
                )
            )
            self.db.flush()
            
        version = self.strategy_version_repo.get_by(strategy_id=strategy.id, version_string="v1.0")
        if not version:
            version = self.strategy_version_repo.create(
                EvaluationStrategyVersion(
                    strategy_id=strategy.id,
                    version_string="v1.0"
                )
            )
            self.db.flush()
            
        return version

    def evaluate_execution(self, execution_id: uuid.UUID, force: bool = False) -> CapabilityProfile:
        """
        Evaluates a completed execution synchronously inside a single transaction.
        load -> validate -> compute -> persist -> aggregate -> commit
        """
        # 1. Load & Validate
        execution = self.execution_repo.get(execution_id)
        if not execution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        if execution.status != ExecutionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Execution must be COMPLETED to evaluate. Current status: {execution.status.value}"
            )

        # Check idempotency
        existing_profile = self.cap_profile_repo.get_by(execution_id=execution_id)
        if existing_profile:
            if not force:
                return existing_profile
            
            # If force=True, we delete the old profile and results, which should cascade
            self.cap_profile_repo.delete(existing_profile.id)
            self.db.flush()
            
            # Delete old evaluation results
            model_outputs = self.model_output_repo.list(execution_id=execution_id)
            output_ids = [mo.id for mo in model_outputs]
            if output_ids:
                old_results = self.db.query(EvaluationResult).filter(EvaluationResult.model_output_id.in_(output_ids)).all()
                for res in old_results:
                    self.db.delete(res)
                self.db.flush()

        # 2. Compute
        model_outputs = self.model_output_repo.list(execution_id=execution_id)
        strategy_version = self._get_or_create_strategy_version()
        
        evaluation_results = []
        total_score = 0.0
        
        for output in model_outputs:
            test_case = self.test_case_repo.get(output.test_case_id)
            if not test_case:
                continue
                
            passed, score, metrics = self.exact_match.evaluate(
                reference=test_case.expected_output,
                prediction=output.raw_output
            )
            
            result = EvaluationResult(
                model_output_id=output.id,
                strategy_version_id=strategy_version.id,
                passed=passed,
                confidence=1.0,
                raw_measurements=metrics,
                reasoning="Computed via ExactMatchStrategy"
            )
            evaluation_results.append(result)
            total_score += score

        # 3. Persist individual results
        for res in evaluation_results:
            self.eval_result_repo.create(res)

        # 4. Aggregate & Persist profile
        overall_score = (total_score / len(evaluation_results)) if evaluation_results else 0.0
        
        profile = self.cap_profile_repo.create(
            CapabilityProfile(
                execution_id=execution_id,
                overall_score=overall_score,
                profile_metadata={
                    "total_outputs": len(model_outputs),
                    "evaluated_outputs": len(evaluation_results),
                    "strategy": "exact_match",
                    "version": "v1.0"
                }
            )
        )

        # 5. Commit happens implicitly by FastAPI dependency (if router calls db.commit)
        # or we explicitly flush here to ensure we have the objects.
        self.db.flush()
        return profile
