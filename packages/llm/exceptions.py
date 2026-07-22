class LLMError(Exception):
    """Base exception for all LLM errors."""

    pass


class LLMConnectionError(LLMError):
    """Raised when unable to connect to the provider."""

    pass


class ModelNotFoundError(LLMError):
    """Raised when the specified model is not available."""

    pass


class GenerationError(LLMError):
    """Raised when the model fails to generate a response."""

    pass


class TimeoutError(LLMError):
    """Raised when a request to the provider times out."""

    pass
