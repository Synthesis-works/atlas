from .base import JudgeProvider, JudgeResponse


class MockJudgeProvider(JudgeProvider):
    """A deterministic mock judge provider for testing."""

    def __init__(
        self,
        default_score: float = 1.0,
        default_reasoning: str = "Mock passed.",
        raise_on_prompt: str | None = None,
    ):
        self.default_score = default_score
        self.default_reasoning = default_reasoning
        self.raise_on_prompt = raise_on_prompt

    def evaluate(self, prompt: str, rubric: str) -> JudgeResponse:
        if self.raise_on_prompt and self.raise_on_prompt in prompt:
            raise ValueError(
                f"Mock failure triggered for prompt containing: {self.raise_on_prompt}"
            )

        return JudgeResponse(
            score=self.default_score,
            reasoning=self.default_reasoning,
            metadata={"provider": "mock", "latency_ms": 10.0},
        )
