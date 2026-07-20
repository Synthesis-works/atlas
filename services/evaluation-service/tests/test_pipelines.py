import pytest
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.pipelines.base import PipelineContext, EvaluationResultBundle, MetricValueModel
from app.pipelines.registry import PipelineRegistry
from app.pipelines.execution import ExecutionPipeline
from app.pipelines.rule import RulePipeline

def test_execution_pipeline():
    context = PipelineContext(
        evaluation_attempt_id=uuid.uuid4(),
        execution_outputs=[
            {"success": True, "output": "Hello world"},
            {"success": False, "output": "Error"},
            {"status": "passed", "output": "Success"}
        ],
        benchmark={"name": "test"},
        configuration={"k": 2}
    )
    
    pipeline = ExecutionPipeline()
    result = pipeline.evaluate(context)
    
    assert isinstance(result, EvaluationResultBundle)
    assert len(result.metrics) == 3
    
    pass_rate = next(m for m in result.metrics if m.name == "pass_rate")
    assert pass_rate.value == 2/3
    
    pass_k = next(m for m in result.metrics if m.name == "pass@2")
    assert pass_k.value == 1.0

def test_rule_pipeline():
    context = PipelineContext(
        evaluation_attempt_id=uuid.uuid4(),
        execution_outputs=[
            {"text": "The secret code is 12345"},
            {"text": "No code here"}
        ],
        benchmark={"name": "test"},
        configuration={"regex_pattern": r"\d{5}"}
    )
    
    pipeline = RulePipeline()
    result = pipeline.evaluate(context)
    
    assert isinstance(result, EvaluationResultBundle)
    assert len(result.metrics) == 1
    
    regex_match = next(m for m in result.metrics if m.name == "regex_match_rate")
    assert regex_match.value == 0.5

def test_invalid_pipeline():
    context = PipelineContext(
        evaluation_attempt_id=uuid.uuid4(),
        execution_outputs=[{"text": "Test"}],
        benchmark={"name": "test"},
        configuration={} # Missing regex_pattern
    )
    
    pipeline = RulePipeline()
    
    with pytest.raises(ValueError, match="requires 'regex_pattern' in configuration"):
        pipeline.evaluate(context)

def test_pipeline_registration():
    # Make sure they are in the registry
    execution_cls = PipelineRegistry.get("ExecutionPipeline")
    rule_cls = PipelineRegistry.get("RulePipeline")
    
    assert execution_cls is ExecutionPipeline
    assert rule_cls is RulePipeline
    
    with pytest.raises(ValueError, match="not found in registry"):
        PipelineRegistry.get("UnknownPipeline")
