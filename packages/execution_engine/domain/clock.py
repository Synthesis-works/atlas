from datetime import UTC, datetime


class Clock:
    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)


class TestClock(Clock):
    def __init__(self, fixed_time: datetime):
        self._fixed_time = fixed_time

    def now(self) -> datetime:  # type: ignore
        return self._fixed_time

    def advance(self, delta):
        self._fixed_time += delta
