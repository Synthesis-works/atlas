from datetime import UTC, datetime


class Clock:
    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)


class TestClock(Clock):
    __test__ = False

    def __init__(self, fixed_time: datetime):
        self._fixed_time = fixed_time

    def now(self) -> datetime:  # type: ignore
        return self._fixed_time

    def advance(self, delta):
        self._fixed_time += delta

    def set_time(self, new_time: datetime):
        self._fixed_time = new_time
