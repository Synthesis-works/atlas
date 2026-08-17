"""
Conftest for tests/execution — the execution-engine domain tests.

These tests use `packages.execution_engine.persistence.models` which maps a
separate SQLAlchemy declarative Base onto the `executions` table.  Running these
tests in the same process as the atlas_db-based tests (which map a *different*
Execution class onto the same table) corrupts the process-wide SQLAlchemy mapper
registry and causes UnmappedColumnError failures in downstream tests.

To prevent cross-contamination we mark every test in this directory with
`@pytest.mark.isolate`.  In CI these should be run in a separate pytest
invocation:

    # Run all atlas_db/app tests
    uv run pytest tests/backend tests/benchmark services/ packages/ -q

    # Run execution-engine domain tests separately
    uv run pytest tests/execution -q

For the default local `uv run pytest -q` (all testpaths) these tests will be
collected but will skip if the `PYTEST_ISOLATION_ALLOWED` env var is not set,
unless explicitly requested with `-m isolate`.
"""

import os
import pytest


def pytest_collection_modifyitems(items, config):
    """
    If PYTEST_ISOLATION_ALLOWED is not set, skip tests marked `isolate` so
    the shared-mapper tests downstream don't get corrupted.
    """
    if os.getenv("PYTEST_ISOLATION_ALLOWED"):
        return

    skip_marker = pytest.mark.skip(
        reason=(
            "Execution-engine domain tests use a separate SQLAlchemy Base that "
            "conflicts with atlas_db models when run in the same process. "
            "Run with PYTEST_ISOLATION_ALLOWED=1 or in a separate pytest invocation."
        )
    )
    for item in items:
        if item.get_closest_marker("isolate"):
            item.add_marker(skip_marker)
