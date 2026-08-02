class DomainException(Exception):
    pass


class InvariantViolationError(DomainException):
    pass


class InvalidStateTransitionError(DomainException):
    pass


class ImmutableExecutionError(DomainException):
    pass


class RetryLimitExceededError(DomainException):
    pass


class LeaseException(DomainException):
    pass


class LeaseExpiredError(LeaseException):
    pass


class LeaseOwnershipError(LeaseException):
    pass


class ExecutionNotFoundError(DomainException):
    pass
