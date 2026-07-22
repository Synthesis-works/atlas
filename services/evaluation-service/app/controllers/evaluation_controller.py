from datetime import UTC, datetime
from uuid import UUID

from app.commands.evaluation import (
    CancelEvaluationJobCommand,
    CompleteEvaluationAttemptCommand,
    CreateEvaluationJobCommand,
    FailEvaluationAttemptCommand,
    StartEvaluationAttemptCommand,
)
from app.events.publisher import EvaluationEventPublisher
from app.events.types import EvaluationEventType
from atlas_db.models.evaluation import (
    AttemptStatus,
    EvaluationArtifact,
    EvaluationAttempt,
    EvaluationJob,
    EvaluationJobStatus,
    EvaluationResult,
    MetricCategory,
    MetricDefinition,
    MetricDirection,
    MetricValue,
)
from sqlalchemy.orm import Session


class EvaluationController:
    """
    Orchestrates the lifecycle of Evaluation Jobs and Attempts.
    The EvaluationController is the only component allowed to mutate EvaluationJob or EvaluationAttempt lifecycle state.
    """

    def __init__(self, db: Session, event_publisher: EvaluationEventPublisher):
        self.db = db
        self.event_publisher = event_publisher

    def execute_create_evaluation_job(self, cmd: CreateEvaluationJobCommand) -> UUID:
        """Handles CreateEvaluationJobCommand"""
        # Create job in PENDING state
        new_job = EvaluationJob(atlas_run_id=cmd.atlas_run_id, status=EvaluationJobStatus.PENDING)
        self.db.add(new_job)
        self.db.flush()

        self.event_publisher.publish_event(
            job_id=str(new_job.id),
            event_type=EvaluationEventType.EVALUATION_JOB_CREATED,
            message="Evaluation job created.",
        )

        self.db.commit()
        return new_job.id

    def execute_start_evaluation_attempt(self, cmd: StartEvaluationAttemptCommand) -> UUID:
        """Handles StartEvaluationAttemptCommand"""
        # Lock the job
        job = self.db.query(EvaluationJob).filter_by(id=cmd.job_id).with_for_update().one_or_none()
        if not job:
            raise ValueError(f"EvaluationJob {cmd.job_id} not found.")

        if job.status in [EvaluationJobStatus.COMPLETED, EvaluationJobStatus.ABORTED]:
            raise ValueError(
                f"Cannot start attempt for job {cmd.job_id} in terminal state {job.status.value}."
            )

        # Check for concurrent running attempts to prevent race conditions
        running_attempts = (
            self.db.query(EvaluationAttempt)
            .filter_by(job_id=cmd.job_id, status=AttemptStatus.RUNNING)
            .count()
        )
        if running_attempts > 0:
            raise ValueError(
                f"Cannot start attempt for job {cmd.job_id} while another attempt is running."
            )

        attempt_number = self.db.query(EvaluationAttempt).filter_by(job_id=cmd.job_id).count() + 1

        # Create new attempt
        new_attempt = EvaluationAttempt(
            job_id=cmd.job_id,
            pipeline_version_id=cmd.pipeline_version_id,
            attempt_number=attempt_number,
            status=AttemptStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self.db.add(new_attempt)

        if job.status == EvaluationJobStatus.PENDING:
            job.status = EvaluationJobStatus.EVALUATING

        self.db.flush()

        # Emit events
        if attempt_number == 1:
            self.event_publisher.publish_event(
                job_id=str(job.id),
                event_type=EvaluationEventType.EVALUATION_STARTED,
                message="Evaluation started.",
            )

        self.event_publisher.publish_event(
            job_id=str(job.id),
            event_type=EvaluationEventType.PIPELINE_STARTED,
            message=f"Pipeline execution started for attempt {new_attempt.id}.",
        )

        self.db.commit()
        return new_attempt.id

    def execute_complete_evaluation_attempt(self, cmd: CompleteEvaluationAttemptCommand) -> None:
        """Handles CompleteEvaluationAttemptCommand"""
        attempt = (
            self.db.query(EvaluationAttempt)
            .filter_by(id=cmd.attempt_id)
            .with_for_update()
            .one_or_none()
        )
        if not attempt:
            raise ValueError(f"EvaluationAttempt {cmd.attempt_id} not found.")

        if attempt.status != AttemptStatus.RUNNING:
            raise ValueError(
                f"Attempt {cmd.attempt_id} cannot be completed from state {attempt.status.value}."
            )

        job = self.db.query(EvaluationJob).filter_by(id=attempt.job_id).with_for_update().one()

        # Create EvaluationResult
        result = EvaluationResult(
            attempt_id=attempt.id,
            artifacts_data={"artifacts_count": len(cmd.result_bundle.artifacts)},
            warnings=cmd.result_bundle.warnings,
            metadata_=cmd.result_bundle.metadata,
        )
        self.db.add(result)
        self.db.flush()

        # Save Metrics
        for metric_model in cmd.result_bundle.metrics:
            # Upsert/Find MetricDefinition
            metric_def = (
                self.db.query(MetricDefinition)
                .filter_by(name=metric_model.name, version="1.0")
                .first()
            )
            if not metric_def:
                metric_def = MetricDefinition(
                    name=metric_model.name,
                    version="1.0",
                    category=MetricCategory(metric_model.category),
                    direction=MetricDirection(metric_model.direction),
                    unit=metric_model.unit,
                )
                self.db.add(metric_def)
                self.db.flush()

            metric_val = MetricValue(
                result_id=result.id,
                metric_def_id=metric_def.id,
                raw_value=metric_model.value,
                normalized_value=metric_model.value,  # Simplifying for now
                source=metric_model.source,
                aggregation=metric_model.aggregation,
                confidence=metric_model.confidence,
                metadata_=metric_model.metadata,
            )
            self.db.add(metric_val)

        # Save JudgeTraces
        # Note: LLM judges are not implemented in 3A/3B, but we support the abstraction
        # We need a dummy judge_version_id to satisfy the foreign key, or we skip since it's execution only.
        # Since the user said "do not introduce LLM judging yet", judge_traces will be empty anyway.
        # But for correctness, if present, we would save them. For now, we skip it or raise error.
        if cmd.result_bundle.judge_traces:
            raise NotImplementedError("Judge traces are not yet supported in Slice 3A.")

        # Save Artifacts
        for artifact_model in cmd.result_bundle.artifacts:
            artifact = EvaluationArtifact(
                attempt_id=attempt.id,
                artifact_hash=artifact_model.artifact_hash,
                target_output=artifact_model.target_output,
                reference_data=artifact_model.reference_data,
                context=artifact_model.context,
            )
            self.db.add(artifact)

        attempt.status = AttemptStatus.COMPLETED
        attempt.completed_at = datetime.now(UTC)

        job.status = EvaluationJobStatus.COMPLETED

        self.event_publisher.publish_event(
            job_id=str(job.id),
            event_type=EvaluationEventType.PIPELINE_COMPLETED,
            message=f"Pipeline execution completed for attempt {attempt.id}.",
        )

        self.event_publisher.publish_event(
            job_id=str(job.id),
            event_type=EvaluationEventType.EVALUATION_COMPLETED,
            message="Evaluation completed successfully.",
        )

        self.db.commit()

    def execute_fail_evaluation_attempt(self, cmd: FailEvaluationAttemptCommand) -> None:
        """Handles FailEvaluationAttemptCommand"""
        attempt = (
            self.db.query(EvaluationAttempt)
            .filter_by(id=cmd.attempt_id)
            .with_for_update()
            .one_or_none()
        )
        if not attempt:
            raise ValueError(f"EvaluationAttempt {cmd.attempt_id} not found.")

        if attempt.status != AttemptStatus.RUNNING:
            raise ValueError(
                f"Attempt {cmd.attempt_id} cannot be failed from state {attempt.status.value}."
            )

        job = self.db.query(EvaluationJob).filter_by(id=attempt.job_id).with_for_update().one()

        attempt.status = AttemptStatus.FAILED
        attempt.completed_at = datetime.now(UTC)
        attempt.error_message = cmd.error_message

        job.status = EvaluationJobStatus.FAILED

        self.event_publisher.publish_event(
            job_id=str(job.id),
            event_type=EvaluationEventType.EVALUATION_FAILED,
            message=f"Evaluation attempt failed: {cmd.error_message}",
        )

        self.db.commit()

    def execute_cancel_evaluation_job(self, cmd: CancelEvaluationJobCommand) -> None:
        """Handles CancelEvaluationJobCommand"""
        job = self.db.query(EvaluationJob).filter_by(id=cmd.job_id).with_for_update().one_or_none()
        if not job:
            raise ValueError(f"EvaluationJob {cmd.job_id} not found.")

        if job.status in [
            EvaluationJobStatus.COMPLETED,
            EvaluationJobStatus.FAILED,
            EvaluationJobStatus.ABORTED,
        ]:
            raise ValueError(f"Job {cmd.job_id} is already in a terminal state.")

        # Cancel any running attempts
        running_attempts = (
            self.db.query(EvaluationAttempt)
            .filter_by(job_id=job.id, status=AttemptStatus.RUNNING)
            .all()
        )

        now = datetime.now(UTC)
        for attempt in running_attempts:
            attempt.status = AttemptStatus.FAILED
            attempt.error_message = "Job cancelled."
            attempt.completed_at = now

        job.status = EvaluationJobStatus.ABORTED

        self.event_publisher.publish_event(
            job_id=str(job.id),
            event_type=EvaluationEventType.EVALUATION_CANCELLED,
            message="Evaluation job cancelled.",
        )

        self.db.commit()
