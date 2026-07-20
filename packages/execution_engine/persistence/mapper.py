from packages.execution_engine.domain.models import Execution, ExecutionAttempt, Lease, Artifact
from packages.execution_engine.persistence.models import ExecutionModel, ExecutionAttemptModel, LeaseModel, ArtifactModel

class ExecutionMapper:
    @staticmethod
    def to_domain(model: ExecutionModel) -> Execution:
        attempts = []
        for am in model.attempts:
            attempt = ExecutionAttempt(
                id=am.id,
                execution_id=am.execution_id,
                attempt_number=am.attempt_number,
                status=am.status,
                started_at=am.started_at,
                finished_at=am.finished_at,
                error_message=am.error_message
            )
            
            if am.lease:
                attempt.lease = Lease(
                    id=am.lease.id,
                    attempt_id=am.lease.attempt_id,
                    worker_id=am.lease.worker_id,
                    acquired_at=am.lease.acquired_at,
                    expires_at=am.lease.expires_at
                )
                
            for arm in am.artifacts:
                attempt.add_artifact(Artifact(
                    id=arm.id,
                    attempt_id=arm.attempt_id,
                    type=arm.type,
                    storage_uri=arm.storage_uri
                ))
            
            attempts.append(attempt)

        return Execution.rehydrate(
            id=model.id,
            benchmark_version_id=model.benchmark_version_id,
            status=model.status,
            created_by=model.created_by_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            max_retries=model.max_retries,
            attempts=attempts
        )

    @staticmethod
    def update_model(execution: Execution, model: ExecutionModel) -> None:
        """Updates the given SQLAlchemy model with data from the domain aggregate."""
        model.status = execution.status
        model.updated_at = execution.updated_at
        model.max_retries = execution.max_retries
        
        # Rebuild attempts
        model_attempts_dict = {a.id: a for a in model.attempts}
        
        for attempt in execution.attempts:
            if attempt.id in model_attempts_dict:
                am = model_attempts_dict[attempt.id]
                am.status = attempt.status
                am.finished_at = attempt.finished_at
                am.error_message = attempt.error_message
            else:
                am = ExecutionAttemptModel(
                    id=attempt.id,
                    execution_id=attempt.execution_id,
                    attempt_number=attempt.attempt_number,
                    status=attempt.status,
                    started_at=attempt.started_at,
                    finished_at=attempt.finished_at,
                    error_message=attempt.error_message
                )
                model.attempts.append(am)
            
            if attempt.lease:
                if not am.lease:
                    am.lease = LeaseModel(
                        id=attempt.lease.id,
                        attempt_id=attempt.lease.attempt_id,
                        worker_id=attempt.lease.worker_id,
                        acquired_at=attempt.lease.acquired_at,
                        expires_at=attempt.lease.expires_at
                    )
                else:
                    am.lease.expires_at = attempt.lease.expires_at
                    # Usually worker_id/acquired_at are immutable but mapping them anyway
                    am.lease.worker_id = attempt.lease.worker_id
                    
            # Map artifacts
            model_artifacts_dict = {a.id: a for a in am.artifacts}
            for artifact in attempt.artifacts:
                if artifact.id not in model_artifacts_dict:
                    am.artifacts.append(ArtifactModel(
                        id=artifact.id,
                        attempt_id=artifact.attempt_id,
                        type=artifact.type,
                        storage_uri=artifact.storage_uri
                    ))

    @staticmethod
    def to_model(execution: Execution) -> ExecutionModel:
        """Creates a brand new SQLAlchemy model from the domain aggregate."""
        model = ExecutionModel(
            id=execution.id,
            benchmark_version_id=execution.benchmark_version_id,
            status=execution.status,
            created_by_id=execution.created_by,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
            max_retries=execution.max_retries
        )
        ExecutionMapper.update_model(execution, model)
        return model
