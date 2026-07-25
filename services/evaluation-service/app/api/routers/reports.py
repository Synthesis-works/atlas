from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


def get_db():
    raise NotImplementedError()


from atlas_db.models.evaluation import (
    CapabilityProfile,
    CapabilityScore,
    EvaluationAttempt,
    EvaluationJob,
    EvaluationResult,
    MetricDefinition,
    MetricValue,
)
from atlas_db.models.execution import ExecutionAdapter, ExecutionAdapterVersion

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/evaluations/{job_id}")
def get_evaluation_report(job_id: UUID, db: Session = Depends(get_db)):
    """Returns the full evaluation tree for a job."""
    job = db.query(EvaluationJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    attempts = db.query(EvaluationAttempt).filter_by(job_id=job.id).all()

    report = {
        "job_id": job.id,
        "run_id": job.atlas_run_id,
        "status": job.status.value,
        "attempts": [],
    }

    for attempt in attempts:
        attempt_data = {
            "attempt_id": attempt.id,
            "status": attempt.status.value,
            "pipeline_version_id": attempt.pipeline_version_id,
            "results": [],
        }

        results = db.query(EvaluationResult).filter_by(attempt_id=attempt.id).all()
        for res in results:
            metrics = db.query(MetricValue).filter_by(result_id=res.id).all()
            attempt_data["results"].append({
                "result_id": res.id,
                "metrics": [
                    {"name": m.metric_name, "value": m.value, "normalized": m.normalized_value}
                    for m in metrics
                ],
            })

        report["attempts"].append(attempt_data)

    return report


@router.get("/capabilities/{adapter_version_id}")
def get_capability_profile(adapter_version_id: UUID, db: Session = Depends(get_db)):
    """Returns the capability profile for a specific adapter version."""
    profile = db.query(CapabilityProfile).filter_by(adapter_version_id=adapter_version_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    scores = db.query(CapabilityScore).filter_by(profile_id=profile.id).all()

    # We'd join with CapabilityDefinition to get the name, but for this slice,
    # we can fetch definitions manually if needed.
    # Assuming capability_definition_id links to a name. Let's just fetch it.
    from atlas_db.models.evaluation import CapabilityDefinition

    score_list = []
    for s in scores:
        cap_def = db.query(CapabilityDefinition).filter_by(id=s.capability_definition_id).first()
        name = cap_def.name if cap_def else "Unknown"
        score_list.append({"capability": name, "score": s.score})

    return {"adapter_version_id": adapter_version_id, "scores": score_list}


@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    """Returns an aggregated view of top capability scores."""
    # Simplified leaderboard: Fetch all profiles, average their scores, and rank them.
    profiles = db.query(CapabilityProfile).all()
    leaderboard = []

    for profile in profiles:
        scores = db.query(CapabilityScore).filter_by(profile_id=profile.id).all()
        if not scores:
            continue
        avg_score = sum(s.score for s in scores) / len(scores)

        # Get adapter name
        adapter_version = (
            db.query(ExecutionAdapterVersion).filter_by(id=profile.adapter_version_id).first()
        )
        adapter_name = "Unknown"
        if adapter_version:
            adapter = db.query(ExecutionAdapter).filter_by(id=adapter_version.adapter_id).first()
            if adapter:
                adapter_name = f"{adapter.name} (v{adapter_version.version_string})"

        leaderboard.append({"adapter": adapter_name, "overall_score": avg_score})

    leaderboard.sort(key=lambda x: x["overall_score"], reverse=True)
    return leaderboard


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """Returns standard metric definitions."""
    definitions = db.query(MetricDefinition).all()
    return [
        {
            "name": d.name,
            "category": d.category.value,
            "direction": d.direction.value,
            "unit": d.unit,
        }
        for d in definitions
    ]
