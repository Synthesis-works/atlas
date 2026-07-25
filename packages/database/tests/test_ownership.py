from datetime import UTC, datetime, timedelta

import pytest
from atlas_db.models.core import (
    Invitation,
    InvitationStatus,
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    Project,
    User,
)
from sqlalchemy.exc import IntegrityError


def test_organization_member_creation(session):
    # Create org
    org = Organization(name="Acme Corp", slug="acme-corp")
    session.add(org)
    session.commit()

    # Create user
    user = User(email="test@acme.com", full_name="Test User", org_id=org.id)
    session.add(user)
    session.commit()

    # Create membership
    member = OrganizationMember(
        user_id=user.id,
        organization_id=org.id,
        role=OrganizationRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    session.add(member)
    session.commit()

    assert member.id is not None
    assert member.role == OrganizationRole.OWNER
    assert member.user.email == "test@acme.com"
    assert member.organization.slug == "acme-corp"


def test_project_ownership_and_unique_constraint(session):
    org = Organization(name="Test Org Ownership", slug="test-org-ownership")
    session.add(org)
    session.commit()

    user = User(email="test2@acme.com", full_name="Test User 2")
    session.add(user)
    session.commit()

    member = OrganizationMember(
        user_id=user.id, organization_id=org.id, role=OrganizationRole.ADMIN
    )
    session.add(member)
    session.commit()

    project1 = Project(
        name="Project Alpha", slug="project-alpha", org_id=org.id, created_by_member_id=member.id
    )
    session.add(project1)
    session.commit()

    assert project1.id is not None
    assert project1.created_by_member_id == member.id

    # Test unique constraint on (org_id, name)
    project2 = Project(name="Project Alpha", slug="project-alpha-2", org_id=org.id)
    session.add(project2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_invitation_lifecycle(session):
    org = Organization(name="Invite Org", slug="invite-org")
    session.add(org)
    session.commit()

    invite = Invitation(
        organization_id=org.id,
        email="newuser@example.com",
        role=OrganizationRole.MEMBER,
        token="secure-token-123",
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(invite)
    session.commit()

    assert invite.id is not None
    assert invite.status == InvitationStatus.PENDING

    invite.status = InvitationStatus.ACCEPTED
    invite.accepted_at = datetime.now(UTC)
    session.commit()

    assert invite.status == InvitationStatus.ACCEPTED
    assert invite.accepted_at is not None
