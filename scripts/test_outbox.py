import datetime
import uuid

from atlas_db.core.session import SessionLocal
from atlas_db.models.outbox import OutboxMessage

from apps.backend.core.telemetry import get_correlation_id
from packages.execution_engine.application.interfaces import EventPublisher
from packages.execution_engine.application.outbox_dispatcher import OutboxDispatcher


class MockEventPublisher(EventPublisher):
    def __init__(self):
        self.should_fail = False
        self.published_events = []
        self.published_correlation_ids = []

    def publish(self, events):
        if self.should_fail:
            raise Exception("Simulated subscriber failure")
        for e in events:
            self.published_events.append(e)
            self.published_correlation_ids.append(get_correlation_id())


def test_schema_and_migrations():
    print("Testing schema...")
    with SessionLocal() as session:
        # Create a test message
        msg_id = uuid.uuid4()
        msg = OutboxMessage(
            outbox_message_id=msg_id,
            event_id=uuid.uuid4(),
            aggregate_id=uuid.uuid4(),
            aggregate_type="TestAggregate",
            event_type="TestEvent",
            payload={"test": "payload"},
            trace_context={"correlation_id": "test-corr-id"},
            occurred_at=datetime.datetime.now(datetime.UTC),
        )
        session.add(msg)
        session.commit()

        # Retrieve it
        retrieved = (
            session.query(OutboxMessage).filter(OutboxMessage.outbox_message_id == msg_id).first()
        )
        assert retrieved is not None
        assert retrieved.status == "PENDING"
        assert retrieved.retry_count == 0
        assert retrieved.trace_context["correlation_id"] == "test-corr-id"

        # Clean up
        session.delete(retrieved)
        session.commit()
    print("Schema test passed.")


def test_successful_dispatch():
    print("Testing successful dispatch...")
    with SessionLocal() as session:
        msg = OutboxMessage(
            event_id=uuid.uuid4(),
            aggregate_id=uuid.uuid4(),
            aggregate_type="Execution",
            event_type="ExecutionCompletedEvent",
            payload={"execution_id": str(uuid.uuid4()), "attempt_id": str(uuid.uuid4())},
            trace_context={"correlation_id": "test-corr-id-success"},
            occurred_at=datetime.datetime.now(datetime.UTC),
        )
        session.add(msg)
        session.commit()
        msg_id = msg.outbox_message_id

    # Dispatch
    publisher = MockEventPublisher()
    with SessionLocal() as session:
        dispatcher = OutboxDispatcher(session, publisher)
        processed = dispatcher.sweep()
        assert processed >= 1

    with SessionLocal() as session:
        retrieved = (
            session.query(OutboxMessage).filter(OutboxMessage.outbox_message_id == msg_id).first()
        )
        assert retrieved.status == "PROCESSED"
        # Cleanup
        session.delete(retrieved)
        session.commit()
    print("Successful dispatch test passed.")


def test_subscriber_failure_and_retry():
    print("Testing failure and retry...")
    with SessionLocal() as session:
        msg = OutboxMessage(
            event_id=uuid.uuid4(),
            aggregate_id=uuid.uuid4(),
            aggregate_type="Execution",
            event_type="ExecutionCompletedEvent",
            payload={"execution_id": str(uuid.uuid4()), "attempt_id": str(uuid.uuid4())},
            trace_context={"correlation_id": "test-corr-id-fail"},
            occurred_at=datetime.datetime.now(datetime.UTC),
        )
        session.add(msg)
        session.commit()
        msg_id = msg.outbox_message_id

    publisher = MockEventPublisher()
    publisher.should_fail = True

    # 1. Sweep - should fail and mark as FAILED
    with SessionLocal() as session:
        dispatcher = OutboxDispatcher(session, publisher)
        processed = dispatcher.sweep()
        assert processed == 0

    with SessionLocal() as session:
        retrieved = (
            session.query(OutboxMessage).filter(OutboxMessage.outbox_message_id == msg_id).first()
        )
        assert retrieved.status == "FAILED"
        assert retrieved.retry_count == 1
        assert retrieved.next_retry_at > retrieved.created_at

        # Fast forward next_retry_at to test retry
        retrieved.next_retry_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            minutes=1
        )
        session.commit()

    # 2. Sweep again with success
    publisher.should_fail = False
    with SessionLocal() as session:
        dispatcher = OutboxDispatcher(session, publisher)
        processed = dispatcher.sweep()
        assert processed >= 1

    with SessionLocal() as session:
        retrieved = (
            session.query(OutboxMessage).filter(OutboxMessage.outbox_message_id == msg_id).first()
        )
        assert retrieved.status == "PROCESSED"
        assert retrieved.retry_count == 1
        session.delete(retrieved)
        session.commit()
    print("Failure and retry test passed.")


def test_poison_message():
    print("Testing poison message...")
    with SessionLocal() as session:
        msg = OutboxMessage(
            event_id=uuid.uuid4(),
            aggregate_id=uuid.uuid4(),
            aggregate_type="Execution",
            event_type="ExecutionCompletedEvent",
            payload={"execution_id": str(uuid.uuid4()), "attempt_id": str(uuid.uuid4())},
            trace_context={"correlation_id": "test-corr-id-poison"},
            occurred_at=datetime.datetime.now(datetime.UTC),
            retry_count=9,  # One attempt away from max
            next_retry_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1),
        )
        session.add(msg)
        session.commit()
        msg_id = msg.outbox_message_id

    publisher = MockEventPublisher()
    publisher.should_fail = True

    with SessionLocal() as session:
        dispatcher = OutboxDispatcher(session, publisher)
        processed = dispatcher.sweep()
        assert processed == 0

    with SessionLocal() as session:
        retrieved = (
            session.query(OutboxMessage).filter(OutboxMessage.outbox_message_id == msg_id).first()
        )
        assert retrieved.status == "DEAD_LETTER"
        assert retrieved.retry_count == 10
        session.delete(retrieved)
        session.commit()
    print("Poison message test passed.")


if __name__ == "__main__":
    test_schema_and_migrations()
    test_successful_dispatch()
    test_subscriber_failure_and_retry()
    test_poison_message()
    print("ALL TESTS PASSED")
