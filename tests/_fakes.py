"""Shared lightweight session stand-ins for API route tests.

Routes that previously relied on ``unittest.mock.Mock()`` sessions now enforce
real authorization, which distinguishes benchmark rows by model and status.
These fakes let existing tests keep their shape while the authorization path
resolves deterministic, typed rows. The filename deliberately avoids the
``test_*`` / ``*_test`` patterns so pytest never collects this module.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from atlas_db.models.authoring import Benchmark, BenchmarkVersion


class FakeQuery:
    """Immutable stand-in query wrapper over a static row list."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = list(rows)

    def filter(self, *criteria: Any, **kwargs: Any) -> FakeQuery:
        return self

    def filter_by(self, **kwargs: Any) -> FakeQuery:
        return self

    def order_by(self, *criteria: Any, **kwargs: Any) -> FakeQuery:
        return self

    def offset(self, value: int) -> FakeQuery:
        return self

    def limit(self, value: int) -> FakeQuery:
        return self

    def first(self) -> Any:
        return self._rows[0] if self._rows else None

    def all(self) -> list[Any]:
        return list(self._rows)

    def count(self) -> int:
        return len(self._rows)

    def __getitem__(self, item: Any) -> Any:
        return self._rows[item]


class FakeDB:
    """Maps a model class to the rows ``db.query(Model)`` will return."""

    def __init__(self, env: dict[type, list[Any]] | None = None) -> None:
        self._env: dict[type, list[Any]] = {key: list(rows) for key, rows in (env or {}).items()}

    def _entity_class(self, entity: Any) -> type:
        return getattr(entity, "class_", entity)

    def query(self, *entities: Any) -> FakeQuery:
        return FakeQuery(self._env.get(self._entity_class(entities[0]), []))

    def add(self, obj: Any) -> None:
        self._env.setdefault(type(obj), []).append(obj)

    def add_all(self, objs: list[Any]) -> None:
        for obj in objs:
            self.add(obj)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, obj: Any) -> None:
        pass

    def flush(self) -> None:
        pass


def published_submission_env(
    *,
    version_id: UUID | None = None,
    benchmark_id: UUID | None = None,
    dataset_version_id: UUID | None = None,
) -> dict[type, list[Any]]:
    """Rows describing a published benchmark version that passes authorization."""
    benchmark_id = benchmark_id or UUID("00000000-0000-0000-0000-0000000000b1")
    version_id = version_id or UUID("00000000-0000-0000-0000-0000000000b2")
    dataset_version_id = dataset_version_id or UUID("00000000-0000-0000-0000-000000000006")
    return {
        BenchmarkVersion: [
            BenchmarkVersion(
                id=version_id,
                benchmark_id=benchmark_id,
                version_string="1.0.0",
                primary_dataset_version_id=dataset_version_id,
            )
        ],
        Benchmark: [
            Benchmark(
                id=benchmark_id,
                project_id=UUID("00000000-0000-0000-0000-0000000000b3"),
                name="Public Benchmark",
                status="published",
                visibility="public",
            )
        ],
    }
