import uuid
from apps.backend.events.snapshot_dispatcher import SnapshotDispatcher
from apps.backend.worker.snapshot_tasks import (
    generate_benchmark_snapshot,
    generate_capability_snapshot,
)


class CelerySnapshotDispatcher(SnapshotDispatcher):
    """
    Celery implementation of the SnapshotDispatcher.
    """

    def dispatch_benchmark_snapshot(
        self, benchmark_version_id: uuid.UUID, execution_id_trigger: uuid.UUID | None
    ) -> None:
        print(f"!!! DISPATCHING BENCHMARK SNAPSHOT {benchmark_version_id}")
        res = generate_benchmark_snapshot.delay(
            str(benchmark_version_id),
            str(execution_id_trigger) if execution_id_trigger else None,
        )
        print(f"!!! BENCHMARK SNAPSHOT DISPATCHED TO REDIS: {res.id}")

    def dispatch_capability_snapshot(
        self, capability_id: uuid.UUID, execution_id_trigger: uuid.UUID | None
    ) -> None:
        print(f"!!! DISPATCHING CAPABILITY SNAPSHOT {capability_id}")
        res = generate_capability_snapshot.delay(
            str(capability_id), str(execution_id_trigger) if execution_id_trigger else None
        )
        print(f"!!! CAPABILITY SNAPSHOT DISPATCHED TO REDIS: {res.id}")
