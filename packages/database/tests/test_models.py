import pytest
from atlas_db.models.core import Configuration, ConfigurationScope, Organization, Project, User
from sqlalchemy.exc import IntegrityError


def test_organization_creation(session):
    org = Organization(name="Test Org")
    session.add(org)
    session.commit()
    assert org.id is not None


def test_project_requires_name(session):
    project = Project(description="No name")
    session.add(project)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_configuration_scope_constraint(session):
    org = Organization(name="Test Org 2")
    session.add(org)
    session.commit()

    project = Project(name="Project 1", org_id=org.id)
    session.add(project)
    session.commit()

    # Should work
    conf1 = Configuration(key="API_URL", scope=ConfigurationScope.ENV)
    session.add(conf1)
    session.commit()

    # Should fail (project_id provided for ENV scope)
    conf2 = Configuration(key="API_URL2", scope=ConfigurationScope.ENV, project_id=project.id)
    session.add(conf2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_fk_constraint(session):
    project = Project(name="Project FK", org_id=None)
    session.add(project)
    session.commit()

    # Invalid organization ID
    import uuid

    invalid_project = Project(name="Invalid FK", org_id=uuid.uuid4())
    session.add(invalid_project)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_cascade_delete(session):
    org = Organization(name="Cascade Org")
    session.add(org)
    session.commit()

    project = Project(name="Cascade Project", org_id=org.id)
    session.add(project)
    session.commit()

    # Add a configuration attached to project (has ondelete='CASCADE')
    conf = Configuration(key="PROJ_CFG", scope=ConfigurationScope.PROJECT, project_id=project.id)
    session.add(conf)
    session.commit()

    conf_id = conf.id

    # Delete project should cascade delete configuration
    session.delete(project)
    session.commit()

    # Check configuration is deleted
    assert session.query(Configuration).filter_by(id=conf_id).first() is None


def test_uniqueness_constraint(session):
    user1 = User(email="unique@example.com", full_name="User 1")
    session.add(user1)
    session.commit()

    user2 = User(email="unique@example.com", full_name="User 2")
    session.add(user2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_optimistic_locking(session):
    org = Organization(name="Versioned Org")
    session.add(org)
    session.commit()

    assert org.version_number == 1

    org.name = "Versioned Org 2"
    session.add(org)
    session.commit()

    assert org.version_number == 2
