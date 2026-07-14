class AtlasException(Exception):
    """Base exception for all Atlas services."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

class ResourceNotFoundError(AtlasException):
    def __init__(self, message: str):
        super().__init__(message, code="NOT_FOUND")

class ValidationError(AtlasException):
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")
