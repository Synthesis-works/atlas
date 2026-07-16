from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
import jwt
import pytest

from apps.backend.main import app
from apps.backend.config import settings
from atlas_db.models.core import OrganizationRole, MembershipStatus, OrganizationMember

client = TestClient(app)

def create_mock_jwt(user_id: str, org_id: str = None, mem_id: str = None):
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    iat = datetime.now(timezone.utc)
    to_encode = {
        "sub": user_id, 
        "exp": expire, 
        "iat": iat, 
        "jti": str(uuid4())
    }
    if org_id:
        to_encode["organization_id"] = org_id
    if mem_id:
        to_encode["membership_id"] = mem_id
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

@pytest.fixture
def mock_dependencies(monkeypatch):
    from apps.backend.authz import require_org_member, require_role
    from apps.backend.dependencies import get_org_service, get_project_service, require_authenticated
    from atlas_db.repositories.core import OrganizationMemberRepository
    
    # We will mock OrganizationMemberRepository.get_by_user_and_org
    mock_repo_instance = MagicMock()
    monkeypatch.setattr("apps.backend.authz.OrganizationMemberRepository", lambda db: mock_repo_instance)
    
    # Mock project repo inside authorize_project_access
    mock_project_repo = MagicMock()
    monkeypatch.setattr("atlas_db.repositories.core.ProjectRepository", lambda db: mock_project_repo)
    
    # Mock org and project services
    mock_org_service = MagicMock()
    app.dependency_overrides[get_org_service] = lambda: mock_org_service
    
    mock_project_service = MagicMock()
    app.dependency_overrides[get_project_service] = lambda: mock_project_service
    
    yield {
        "member_repo": mock_repo_instance,
        "project_repo": mock_project_repo,
        "org_service": mock_org_service,
        "project_service": mock_project_service
    }
    
    app.dependency_overrides.clear()

def test_cross_org_access(mock_dependencies):
    user_id = str(uuid4())
    org_id = str(uuid4())
    token = create_mock_jwt(user_id)
    
    # Mock user NOT being in the org
    mock_dependencies["member_repo"].get_by_user_and_org.return_value = None
    
    response = client.get(f"/api/v1/organizations/{org_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "You are not an active member of this organization."

def test_privilege_escalation_viewer_cannot_create_project(mock_dependencies):
    user_id = str(uuid4())
    org_id = str(uuid4())
    token = create_mock_jwt(user_id)
    
    # Mock user is VIEWER
    viewer_member = OrganizationMember(id=uuid4(), user_id=uuid4(), organization_id=uuid4(), role=OrganizationRole.VIEWER, status=MembershipStatus.ACTIVE)
    mock_dependencies["member_repo"].get_by_user_and_org.return_value = viewer_member
    
    # Attempt to POST project
    response = client.post(
        f"/api/v1/organizations/{org_id}/projects", 
        json={"name": "My Project", "slug": "my-project", "description": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert "Operation not permitted" in response.json()["error"]["message"]

def test_inactive_membership(mock_dependencies):
    user_id = str(uuid4())
    org_id = str(uuid4())
    token = create_mock_jwt(user_id)
    
    # Mock user is SUSPENDED
    inactive_member = OrganizationMember(id=uuid4(), user_id=uuid4(), organization_id=uuid4(), role=OrganizationRole.OWNER, status=MembershipStatus.SUSPENDED)
    mock_dependencies["member_repo"].get_by_user_and_org.return_value = inactive_member
    
    response = client.get(f"/api/v1/organizations/{org_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "You are not an active member of this organization."

def test_owner_can_create_project(mock_dependencies):
    user_id = str(uuid4())
    org_id = str(uuid4())
    token = create_mock_jwt(user_id)
    
    owner_member = OrganizationMember(id=uuid4(), user_id=uuid4(), organization_id=uuid4(), role=OrganizationRole.OWNER, status=MembershipStatus.ACTIVE)
    mock_dependencies["member_repo"].get_by_user_and_org.return_value = owner_member
    
    mock_project = MagicMock(
        id=uuid4(), slug="my-project", description="", 
        org_id=uuid4(), created_by_member_id=uuid4(), updated_by_member_id=uuid4(), created_at=datetime.now()
    )
    mock_project.name = "My Project"
    mock_dependencies["project_service"].create.return_value = mock_project
    
    # Mock schemas correctly for validation
    response = client.post(
        f"/api/v1/organizations/{org_id}/projects", 
        json={"name": "My Project", "slug": "my-project", "description": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
