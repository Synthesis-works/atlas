class BaseRuntimeException(Exception):
    """Base exception for all runtime errors."""
    pass

class ExecutionTimeoutException(BaseRuntimeException):
    """Raised when an execution exceeds its time limit."""
    pass

class CompilationException(BaseRuntimeException):
    """Raised when source code fails to compile or parse."""
    pass

class SecurityException(BaseRuntimeException):
    """Raised when source code violates security policies (e.g. invalid AST nodes)."""
    pass

class SandboxException(BaseRuntimeException):
    """Raised when the sandbox fails to initialize or cleanup."""
    pass
