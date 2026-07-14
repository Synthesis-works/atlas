from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.controllers.evaluation_controller import EvaluationController
from app.commands.evaluation import (
    CreateEvaluationJobCommand,
    StartEvaluationAttemptCommand,
    CompleteEvaluationAttemptCommand,
    FailEvaluationAttemptCommand
)
from app.pipelines.base import PipelineContext
from app.pipelines.registry import PipelineRegistry
from app.engine.metrics import MetricEngine
from app.engine.capabilities import CapabilityEngine

# For accessing execution data
from atlas_db.models.execution import AtlasRun, ModelOutput
from atlas_db.models.evaluation import EvaluationPipeline, EvaluationPipelineVersion, CapabilityProfile, CapabilityScore

class EvaluationOrchestrator:
    """
    Coordinates the end-to-end evaluation flow when a run completes.
    Reads from Execution, writes to Evaluation via Controller.
    """
    def __init__(self, db: Session, controller: EvaluationController, metric_engine: MetricEngine, capability_engine: CapabilityEngine):
        self.db = db
        self.controller = controller
        self.metric_engine = metric_engine
        self.capability_engine = capability_engine

    def handle_run_completed(self, run_id: UUID) -> None:
        """Triggered when an execution run completes."""
        
        # 1. Fetch Run and Outputs
        run = self.db.query(AtlasRun).filter_by(id=run_id).one_or_none()
        if not run:
            raise ValueError(f"Run {run_id} not found.")

        outputs = self.db.query(ModelOutput).filter_by(atlas_run_id=run_id).all()
        execution_outputs = [{"text": out.raw_output, "tokens_used": out.tokens_used, "duration_ms": out.duration_ms} for out in outputs]

        # 2. Determine Pipeline (Simple resolution for demonstration)
        # In a real app, this might be linked to the BenchmarkVersion. We'll find or create a default 'ExecutionPipeline'.
        pipeline = self.db.query(EvaluationPipeline).filter_by(name="ExecutionPipeline").first()
        if not pipeline:
            pipeline = EvaluationPipeline(name="ExecutionPipeline", description="Default Execution Pipeline")
            self.db.add(pipeline)
            self.db.flush()
            
        pipeline_version = self.db.query(EvaluationPipelineVersion).filter_by(pipeline_id=pipeline.id).order_by(EvaluationPipelineVersion.version.desc()).first()
        if not pipeline_version:
            pipeline_version = EvaluationPipelineVersion(pipeline_id=pipeline.id, version="1.0", config_schema={"k": 1})
            self.db.add(pipeline_version)
            self.db.flush()

        # 3. Create Job & Start Attempt
        cmd_create = CreateEvaluationJobCommand(atlas_run_id=run.id)
        job_id = self.controller.execute_create_evaluation_job(cmd_create)

        cmd_start = StartEvaluationAttemptCommand(job_id=job_id, pipeline_version_id=pipeline_version.id)
        attempt_id = self.controller.execute_start_evaluation_attempt(cmd_start)

        try:
            # 4. Execute Pipeline
            pipeline_cls = PipelineRegistry.get(pipeline.name)
            pipeline_instance = pipeline_cls()
            
            context = PipelineContext(
                evaluation_attempt_id=attempt_id,
                execution_outputs=execution_outputs,
                benchmark={"id": str(run.benchmark_version_id)},
                configuration=pipeline_version.config_schema or {}
            )
            
            result_bundle = pipeline_instance.evaluate(context)

            # 5. Metric Engine
            result_bundle.metrics = self.metric_engine.process(result_bundle.metrics)

            # 6. Complete Attempt (Controller persists results and metrics)
            cmd_complete = CompleteEvaluationAttemptCommand(
                attempt_id=attempt_id,
                result_bundle=result_bundle
            )
            self.controller.execute_complete_evaluation_attempt(cmd_complete)

            # 7. Capability Engine
            # Run capability mapping against the finalized metrics
            # Note: In our current architecture, CapabilityProfiles are per adapter_version, not per run,
            # but they aggregate metrics across runs. For simplicity in Slice 6, we just generate one profile per adapter based on this run's metrics.
            profile_model = self.capability_engine.process(run.adapter_version_id, result_bundle.metrics)
            
            # Persist Capability Profile
            profile = CapabilityProfile(
                adapter_version_id=profile_model.adapter_version_id
            )
            self.db.add(profile)
            self.db.flush()

            # Need definitions for capability scores
            from atlas_db.models.evaluation import CapabilityDefinition
            for score_model in profile_model.scores:
                cap_def = self.db.query(CapabilityDefinition).filter_by(name=score_model.capability_name).first()
                if not cap_def:
                    cap_def = CapabilityDefinition(name=score_model.capability_name)
                    self.db.add(cap_def)
                    self.db.flush()
                
                score_entity = CapabilityScore(
                    profile_id=profile.id,
                    capability_definition_id=cap_def.id,
                    score=score_model.score
                )
                self.db.add(score_entity)
            
            self.db.commit()

        except Exception as e:
            # Fail attempt on error
            self.db.rollback()
            cmd_fail = FailEvaluationAttemptCommand(attempt_id=attempt_id, error_message=str(e))
            self.controller.execute_fail_evaluation_attempt(cmd_fail)
            raise e
