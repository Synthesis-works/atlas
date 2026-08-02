from .extractors.code_block import CodeBlockExtractor
from .extractors.noop import NoopExtractor
from .extractors.regex import RegexExtractor
from .judges.selector import JudgeSelector
from .normalizers.lowercase import LowercaseNormalizer
from .normalizers.noop import NoopNormalizer
from .normalizers.whitespace import WhitespaceNormalizer
from .results.status import EvaluationStatus


class EvaluationPipeline:
    def __init__(self):
        self.extractors = {
            "noop": NoopExtractor(),
            "regex": RegexExtractor(r"(.*)"),
            "code_block": CodeBlockExtractor(),
        }
        self.normalizers = {
            "noop": NoopNormalizer(),
            "whitespace": WhitespaceNormalizer(),
            "lowercase": LowercaseNormalizer(),
        }
        self.judge_selector = JudgeSelector()

    def evaluate(self, config, expected: str, actual: str):
        extractor = self.extractors.get(config.extractor, NoopExtractor())
        normalizer = self.normalizers.get(config.normalizer, NoopNormalizer())
        judge = self.judge_selector.get_judge(config.judge)

        try:
            extracted = extractor.extract(actual)
            normalized = normalizer.normalize(extracted)
            # We also normalize the expected output so they match format
            expected_normalized = normalizer.normalize(str(expected))
            passed, score, confidence = judge.evaluate(expected_normalized, normalized)

            status = EvaluationStatus.PASS if passed else EvaluationStatus.FAIL
            return status, normalized, score, confidence
        except Exception:
            return EvaluationStatus.ERROR, actual, 0.0, 0.0
