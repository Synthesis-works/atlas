import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.engine.capabilities import CapabilityEngine
from app.pipelines.base import MetricValueModel


def test_capability_engine():
    engine = CapabilityEngine()

    metrics = [
        MetricValueModel(
            name="pass_rate",
            value=0.9,
            normalized_value=0.9,
            category="CORRECTNESS",
            direction="HIGHER",
            unit="percent",
            source="exec",
            aggregation="mean",
        ),
        MetricValueModel(
            name="judge_score",
            value=0.8,
            normalized_value=0.8,
            category="QUALITY",
            direction="HIGHER",
            unit="score",
            source="judge",
            aggregation="mean",
        ),
    ]

    adapter_id = uuid.uuid4()
    profile = engine.process(adapter_id, metrics)

    assert profile.adapter_version_id == adapter_id
    assert len(profile.scores) == 2

    coding_score = next(s for s in profile.scores if s.capability_name == "Coding")
    assert coding_score.score == 0.9

    reasoning_score = next(s for s in profile.scores if s.capability_name == "Reasoning")
    assert reasoning_score.score == 0.8
