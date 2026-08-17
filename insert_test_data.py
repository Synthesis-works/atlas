import sys
import uuid
from sqlalchemy import create_engine, MetaData, insert

try:
    engine = create_engine("postgresql://postgres:postgres@localhost:5432/test_upgrade_safety")
    metadata = MetaData()
    metadata.reflect(bind=engine)

    users = metadata.tables["users"]
    orgs = metadata.tables["organizations"]
    projs = metadata.tables["projects"]
    datasets = metadata.tables["datasets"]

    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    proj_id = str(uuid.uuid4())
    dataset_id = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(
            insert(users).values(
                id=user_id, email="test@test.com", full_name="test", is_active=True
            )
        )
        conn.execute(insert(orgs).values(id=org_id, name="testorg", slug="testorg"))
        conn.execute(
            insert(projs).values(
                id=proj_id, name="testproj", organization_id=org_id, created_by_id=user_id
            )
        )
        conn.execute(
            insert(datasets).values(
                id=dataset_id, name="testds", status="ACTIVE", project_id=proj_id
            )
        )

    print("Test data inserted successfully.")
except Exception as e:
    print(f"Failed to insert: {e}")
    sys.exit(1)
