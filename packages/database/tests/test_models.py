import pytest
from atlas_db.models.core import Organization, Project, Configuration, ConfigurationScope
from atlas_db.models.evaluation import EvaluationStrategy, StrategyType
from atlas_db.models.dataset import DatasetRegistry
from sqlalchemy.exc import IntegrityError

def test_organization_creation(session):
    org = Organization(name="Test Org")
    session.add(org)
    session.commit()
    
    assert org.id is not None
    assert org.created_at is not None
    assert org.version_number == 1

def test_project_requires_name(session):
    project = Project()
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
    
    conf2 = Configuration(key="PROJ_VAR", scope=ConfigurationScope.PROJECT, project_id=project.id)
    session.add(conf2)
    session.commit()
    
    # Should fail constraint
    conf3 = Configuration(key="BAD_VAR", scope=ConfigurationScope.PROJECT)
    session.add(conf3)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

def test_evaluation_strategy_creation(session):
    strategy = EvaluationStrategy(name="F1 Score", type=StrategyType.EXACT_MATCH)
    session.add(strategy)
    session.commit()
    assert strategy.id is not None
