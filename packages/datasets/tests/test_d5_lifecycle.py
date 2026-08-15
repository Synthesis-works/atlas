import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from apps.backend.main import app
from apps.backend.dependencies import require_authenticated
from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.core import OrganizationMember, OrganizationRole
from atlas_db.models.dataset import DatasetExportAction, DatasetExportState
from packages.database.tests.test_d2_postgres_integration import setup_d2_fixtures, postgres_engine, pg_session

pytestmark = pytest.mark.asyncio

class RuntimeAuthContext:
    user_id: uuid.UUID = uuid.uuid4()

def override_auth():
    import time
    now = int(time.time())
    return TokenClaims(sub=RuntimeAuthContext.user_id, email="test@example.com", exp=now+3600, iat=now, jti=str(uuid.uuid4()))
    
class MockAuthz:
    def authorize_project_access(self, *args, **kwargs):
        from atlas_db.models.core import OrganizationRole, OrganizationMember
        return OrganizationMember(id=uuid.uuid4(), role=OrganizationRole.OWNER, user_id=RuntimeAuthContext.user_id)

def override_authz():
    return MockAuthz()

from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_db_sessions(pg_session):
    with patch("apps.backend.routers.datasets.SessionLocal", return_value=pg_session), \
         patch("apps.backend.worker.dataset_tasks.SessionLocal", return_value=pg_session):
        yield

from apps.backend.dependencies import get_db_session

@pytest.fixture(autouse=True)
def setup_auth_overrides(pg_session):
    with patch("apps.backend.routers.datasets.run_dataset_export_task.delay") as mock_delay:
        app.dependency_overrides[require_authenticated] = override_auth
        app.dependency_overrides[get_project_authz_service] = override_authz
        app.dependency_overrides[get_db_session] = lambda: pg_session
        yield
        app.dependency_overrides.clear()

async def test_d5_export_lifecycle_api(pg_session):
    dv_id = setup_d2_fixtures(pg_session)
    from atlas_db.models.dataset import DatasetVersion
    dv = pg_session.query(DatasetVersion).filter(DatasetVersion.id == dv_id).first()
    project_id = dv.dataset.project_id
    dataset_id = dv.dataset_id
    from atlas_db.models.core import User
    active_user = User(id=uuid.uuid4(), email="real.d5.tester@example.com", full_name="D5 Tester")
    pg_session.add(active_user)
    pg_session.commit()
    RuntimeAuthContext.user_id = active_user.id
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Post to create export
            url = f"/api/v1/projects/{project_id}/datasets/{dataset_id}/exports"
            resp = await client.post(url)
            if resp.status_code != 202:
                assert False, f"FAILED POST: {resp.status_code} - {resp.text}"
            print(f"Error detail: {resp.text}")
            assert resp.status_code == status.HTTP_202_ACCEPTED
            export_data = resp.json()
            export_id = export_data["id"]
            assert export_data["status"] == "pending"
            
            # 2. Get list of exports
            list_resp = await client.get(url)
            if list_resp.status_code != 200:
                assert False, f"FAILED GET LIST: {list_resp.status_code} - {list_resp.text}"
            assert list_resp.status_code == status.HTTP_200_OK
            assert len(list_resp.json()) == 1
            assert list_resp.json()[0]["id"] == export_id
            
            # 3. Get single export
            get_resp = await client.get(f"{url}/{export_id}")
            if get_resp.status_code != 200:
                assert False, f"FAILED GET SINGLE: {get_resp.status_code} - {get_resp.text}"
            assert get_resp.status_code == status.HTTP_200_OK
            assert get_resp.json()["id"] == export_id
            
            # 4. Try download incomplete (should be 400 Bad Request)
            down_resp = await client.get(f"{url}/{export_id}/download")
            if down_resp.status_code != 400:
                print("FAILED BAD REQUEST CHECK:", down_resp.status_code, down_resp.text)
            assert down_resp.status_code == status.HTTP_400_BAD_REQUEST
            
            # 5. Simulate worker completion (in real scenario handled by celery)
            action = pg_session.query(DatasetExportAction).filter_by(id=export_id).first()
            action.status = DatasetExportState.COMPLETED
            # We need a dummy file
            import tempfile, os
            fd, path = tempfile.mkstemp(suffix=".jsonl")
            os.write(fd, b'{"hello":"world"}\n')
            os.close(fd)
            
            import apps.backend.config
            # We use a dummy local store resolution
            action.artifact_uri = f"artifact://datasets/{dv_id}/dummy.jsonl"
            # We have to write the actually expected file to the default artifacts path!
            artifact_store_path = getattr(apps.backend.config.settings, "artifact_storage_path", "/tmp/atlas_artifacts")
            dummy_dir = os.path.join(artifact_store_path, str(dv_id))
            os.makedirs(dummy_dir, exist_ok=True)
            import shutil
            shutil.copy2(path, os.path.join(dummy_dir, "dummy.jsonl"))
    
            pg_session.commit()
            
            # 6. Try download completed
            down_success = await client.get(f"{url}/{export_id}/download")
            assert down_success.status_code == status.HTTP_200_OK
            
            os.remove(path)
    except Exception:
        raise
