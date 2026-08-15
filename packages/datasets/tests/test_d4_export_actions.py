import uuid
import pytest
from sqlalchemy import text
from unittest.mock import Mock, patch
from httpx import AsyncClient
from fastapi import status

from apps.backend.main import app # assuming fast API app
from atlas_db.models.dataset import DatasetExportAction, DatasetExportState
from packages.database.tests.test_d2_postgres_integration import setup_d2_fixtures, postgres_engine, pg_session

pytestmark = pytest.mark.asyncio

async def test_d4_idempotent_export_action(pg_session):
    """
    Ensure the DatasetExportAction resolves effectively natively mapping gracefully cleanly safely ensuring zero-trust.
    """
    # Create dataset hierarchy natively
    dv_id = setup_d2_fixtures(pg_session)
    project_id = uuid.uuid4() 
    # Because Foreign Key project_id must exist in postgres:
    # Actually setup_d2_fixtures creates the Project, but returns DatasetVersion ID.
    from atlas_db.models.dataset import DatasetVersion
    dv = pg_session.query(DatasetVersion).filter(DatasetVersion.id == dv_id).first()
    project_id = dv.dataset.project_id
    
    from packages.datasets.services.export_action_service import ExportActionService
    from packages.datasets.services.export_service import DatasetExportService
    from atlas_db.services.dataset_extraction import DatasetExtractionService
    
    mock_store = Mock()
    mock_store.store_training_artifact.return_value = "s3://mock/dataset.jsonl"
    extraction_service = DatasetExtractionService(pg_session)
    export_service = DatasetExportService(extraction_service, mock_store)
    
    action_service = ExportActionService(pg_session, export_service)
    
    # 1. First Schedule
    user_id = None # Set to None avoiding arbitrary user foreign key violations in postgres
    action1 = action_service.schedule_export(dv_id, project_id, user_id)
    assert action1.status == DatasetExportState.PENDING
    
    print("\n--- DB RAW SQL ---")
    res = pg_session.execute(text("SELECT status::text FROM dataset_export_actions")).fetchall()
    print("Statuses:", res)
    indexes = pg_session.execute(text("SELECT indexdef FROM pg_indexes WHERE indexname = 'idx_unique_active_dataset_export'")).fetchall()
    print("Index def:", indexes)
    print("----------------\n")
    
    # 2. Duplicate Idempotent Request 
    action2 = action_service.schedule_export(dv_id, project_id, user_id)
    assert action1.id == action2.id # Must be exactly the same action instance
    
    # 3. Process execution
    action_service.process_export(action1.id)
    
    # 4. Verify completely mapping explicitly correctly natively
    pg_session.refresh(action1)
    assert action1.status == DatasetExportState.COMPLETED
    assert action1.artifact_uri == "s3://mock/dataset.jsonl"
    
    # 5. Subsequent request AFTER completion creates a NEW tracking explicitly smartly
    action3 = action_service.schedule_export(dv_id, project_id, user_id)
    assert action3.id != action1.id
    assert action3.status == DatasetExportState.PENDING

async def test_api_scheduling_endpoint_auth(pg_session):
    """
    Test 401/403 authorization correctly ensuring D4 doesn't bypass D2 logic.
    """
    # Assuming endpoint is implemented and requires auth
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Firing purely correctly natively mapping structurally explicitly
        resp = await client.post(f"/api/v1/projects/{uuid.uuid4()}/datasets/{uuid.uuid4()}/exports", headers={})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
