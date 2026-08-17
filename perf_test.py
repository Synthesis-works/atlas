import asyncio
import uuid
import time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event, text
from packages.database.atlas_db.services.dataset_extraction import DatasetExtractionService
import packages.database.atlas_db.models.dataset as ds
import packages.database.atlas_db.models.tasks as ts
from packages.database.atlas_db.models.base import Base

query_count = 0


def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    global query_count
    query_count += 1


async def run_perf():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_alembic_isolation",
        pool_pre_ping=True,
    )
    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    ds_id, dsv_id = uuid.uuid4(), uuid.uuid4()
    async with async_session() as session:
        session.add(
            ds.Dataset(
                id=ds_id,
                project_id=uuid.uuid4(),
                name="perf",
                version="1",
                license_id=uuid.uuid4(),
                registry_id=uuid.uuid4(),
                source_id=uuid.uuid4(),
            )
        )
        session.add(ds.DatasetVersion(id=dsv_id, dataset_id=ds_id, version_hash="x"))
        await session.commit()

        async def make_tasks(n):
            for i in range(n):
                t = ts.Task(
                    id=uuid.uuid4(),
                    title=f"t{i}",
                    dataset_version_id=dsv_id,
                    input_data={},
                    expected_output={},
                    evaluation_strategy="x",
                )
                session.add(t)
                session.add(
                    ts.Prompt(id=uuid.uuid4(), task_id=t.id, system_prompt="s", user_prompt="u")
                )
                session.add(
                    ts.TestCase(
                        id=uuid.uuid4(),
                        task_id=t.id,
                        input_data={"a": 1},
                        expected_output={"b": 1},
                        is_canonical=True,
                    )
                )
            await session.commit()

        service = DatasetExtractionService(async_session)

        await make_tasks(1)
        global query_count
        query_count = 0
        await service.extract_sft_dataset(dsv_id)
        print(f"1 task: {query_count} queries")

        await make_tasks(9)
        query_count = 0
        await service.extract_sft_dataset(dsv_id)
        print(f"10 tasks: {query_count} queries")

        await make_tasks(90)
        query_count = 0
        await service.extract_sft_dataset(dsv_id)
        print(f"100 tasks: {query_count} queries")


asyncio.run(run_perf())
