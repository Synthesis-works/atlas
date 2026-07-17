import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import MagicMock

from apps.backend.main import app
from apps.backend.dependencies import get_org_service, get_project_service, get_current_member
from apps.backend.schemas.organizations import OrganizationMemberRead
from atlas_db.models.core import Organization, OrganizationRole, MembershipStatus, Project, Invitation, InvitationStatus

client = TestClient(app)

mock_org_service = MagicMock()
mock_project_service = MagicMock()

def override_get_org_service():
    return mock_org_service

def override_get_project_service():
    return mock_project_service

MOCK_MEMBER = OrganizationMemberRead(
    id=uuid4(),
    user_id=uuid4(),
    organization_id=uuid4(),
    role=OrganizationRole.OWNER,
    status=MembershipStatus.ACTIVE,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc)
)

def override_get_current_member():
    return MOCK_MEMBER

def override_get_current_user():
    from atlas_db.models.core import User
    return User(id=uuid4(), email="test@example.com", is_active=True, is_verified=True, full_name="Test User")

app.dependency_overrides[get_org_service] = override_get_org_service
app.dependency_overrides[get_project_service] = override_get_project_service
app.dependency_overrides[get_current_member] = override_get_current_member
from apps.backend.dependencies import get_current_user
app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture(autouse=True)
def reset_mocks():
    mock_org_service.reset_mock()
    mock_project_service.reset_mock()

def test_organization_create_and_list():
    org_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_org_service.create.return_value = Organization(
        id=org_id, name="Acme Corp", slug="acme-corp", 
        created_at=now, updated_at=now
    )
    mock_org_service.list_for_user.return_value = [Organization(
        id=org_id, name="Acme Corp", slug="acme-corp",
        created_at=now, updated_at=now
    )]

    response = client.post("/api/v1/organizations", json={
        "name": "Acme Corp",
        "slug": "acme-corp",
        "display_name": "Acme Corporation"
    })
    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Acme Corp"

    response = client.get("/api/v1/organizations")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

def test_project_create():
    org_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_project_service.create.return_value = Project(
        id=uuid4(), name="Project Alpha", slug="project-alpha", org_id=org_id,
        created_at=now, updated_at=now
    )
    
    response = client.post(f"/api/v1/organizations/{org_id}/projects", json={
        "name": "Project Alpha",
        "slug": "project-alpha"
    })
    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Project Alpha"

def test_invitation_invite():
    org_id = uuid4()
    mock_org_service.invite_member.return_value = Invitation(
        id=uuid4(), organization_id=org_id, email="test@example.com", 
        role=OrganizationRole.MEMBER, status=InvitationStatus.PENDING,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc)
    )

    response = client.post(f"/api/v1/organizations/{org_id}/members", json={
        "email": "test@example.com",
        "role": "member"
    })
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "test@example.com"

