import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.engine.metrics import MetricEngine
from app.pipelines.base import MetricValueModel


def test_metric_engine_validation():
    engine = MetricEngine(validation_rules={"test_metric": {"min_value": 0.0, "max_value": 1.0}})

    valid_metric = MetricValueModel(
        name="test_metric",
        value=0.5,
        category="QUALITY",
        direction="HIGHER",
        unit="score",
        source="test",
        aggregation="mean",
    )
    assert len(engine.validate([valid_metric])) == 1

    invalid_metric = MetricValueModel(
        name="test_metric",
        value=1.5,
        category="QUALITY",
        direction="HIGHER",
        unit="score",
        source="test",
        aggregation="mean",
    )
    with pytest.raises(ValueError, match="is above maximum"):
        engine.validate([invalid_metric])


def test_metric_engine_normalization():
    engine = MetricEngine(validation_rules={"test_metric": {"min_value": 0.0, "max_value": 10.0}})
    metric = MetricValueModel(
        name="test_metric",
        value=5.0,
        category="QUALITY",
        direction="HIGHER",
        unit="score",
        source="test",
        aggregation="mean",
    )
    normalized = engine.normalize([metric])
    assert normalized[0].normalized_value == 0.5


def test_metric_engine_aggregation():
    engine = MetricEngine()
    m1 = MetricValueModel(
        name="test_metric",
        value=5.0,
        normalized_value=0.5,
        category="QUALITY",
        direction="HIGHER",
        unit="score",
        source="test",
        aggregation="mean",
    )
    m2 = MetricValueModel(
        name="test_metric",
        value=9.0,
        normalized_value=0.9,
        category="QUALITY",
        direction="HIGHER",
        unit="score",
        source="test",
        aggregation="mean",
    )
    aggregated = engine.aggregate([m1, m2])
    assert len(aggregated) == 1
    assert aggregated[0].value == 7.0
    assert aggregated[0].normalized_value == 0.7
