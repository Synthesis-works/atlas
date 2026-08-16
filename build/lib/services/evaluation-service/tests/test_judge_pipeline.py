import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.judges.mock import MockJudgeProvider
from app.pipelines.base import PipelineContext
from app.pipelines.judge import JudgePipeline


def test_judge_pipeline():
    context = PipelineContext(
        evaluation_attempt_id=uuid.uuid4(),
        execution_outputs=[{"text": "Sample output 1"}, {"text": "Sample output 2"}],
        benchmark={"name": "test"},
        configuration={"rubric": "Does it make sense?", "prompt_template": "Evaluate: {output}"},
    )

    provider = MockJudgeProvider(default_score=0.8, default_reasoning="Looks good.")
    pipeline = JudgePipeline(provider=provider)

    result = pipeline.evaluate(context)

    assert len(result.judge_traces) == 2
    assert result.judge_traces[0].prompt == "Evaluate: Sample output 1"
    assert result.judge_traces[0].rubric == "Does it make sense?"
    assert result.judge_traces[0].response == "Looks good."

    assert len(result.metrics) == 1
    assert result.metrics[0].name == "judge_score"
    assert result.metrics[0].value == 0.8
    assert result.metrics[0].category == "QUALITY"


def test_judge_pipeline_invalid_provider():
    context = PipelineContext(
        evaluation_attempt_id=uuid.uuid4(),
        execution_outputs=[{"text": "bad_prompt"}],
        benchmark={"name": "test"},
        configuration={},
    )

    provider = MockJudgeProvider(raise_on_prompt="bad_prompt")
    pipeline = JudgePipeline(provider=provider)

    with pytest.raises(
        ValueError, match="Mock failure triggered for prompt containing: bad_prompt"
    ):
        pipeline.evaluate(context)
