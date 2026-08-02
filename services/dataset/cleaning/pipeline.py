import abc


class CleaningStep(abc.ABC):
    @abc.abstractmethod
    def apply(self, data: bytes) -> bytes:
        pass


class NormalizeWhitespace(CleaningStep):
    def apply(self, data: bytes) -> bytes:
        # Simple example: replace multiple spaces with single space
        text = data.decode("utf-8")
        cleaned = " ".join(text.split())
        return cleaned.encode("utf-8")


class CleaningPipeline:
    """
    Executes a sequence of cleaning steps on raw data.
    Note: Cleaning creates a processed artifact; it does not replace the raw upload.
    """

    def __init__(self, steps: list[CleaningStep]):
        self.steps = steps

    def execute(self, raw_data: bytes) -> bytes:
        processed_data = raw_data
        for step in self.steps:
            processed_data = step.apply(processed_data)
        return processed_data
