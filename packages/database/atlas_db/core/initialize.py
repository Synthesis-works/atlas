import logging
import uuid
from sqlalchemy.engine import Engine
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from atlas_db.core.base import Base

# Import all models to register them on the metadata
import atlas_db.models
import packages.execution_engine.persistence.models

logger = logging.getLogger(__name__)

REQUIRED_TABLES = [
    "datasets",
    "benchmarks",
    "benchmark_versions",
    "tasks",
    "prompts",
    "test_cases",
    "executions",
    "model_outputs",
    "evaluation_results",
    "reports",
    "report_versions",
]

# Default identities referenced by the agent tools and execution engine when
# running without an explicit project/user context. They must exist for
# foreign-key constraints on fresh databases (PostgreSQL enforces FKs; local
# SQLite historically did not).
DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

# The execution engine persists DBExecution rows with a fixed project id.
DEFAULT_EXECUTION_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
# Referenced by agent tooling when assigning execution lineage users.
DEFAULT_EXECUTION_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

# Organization that hosts the default agent identities (required so the
# execution engine's organization_members foreign key resolves).
DEFAULT_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-00000000000a")


def initialize_database_schema(engine: Engine) -> None:
    """
    Initialize database schemas and tables on the target engine.
    Ensures all models are fully registered, and verifies that the required tables exist.
    """
    logger.info(f"Initializing database schema on engine: {engine.url}")

    # 1. Create tables
    Base.metadata.create_all(bind=engine)

    # 2. Verify all required tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    logger.info(f"Existing tables in database: {existing_tables}")

    missing_tables = [table for table in REQUIRED_TABLES if table not in existing_tables]
    if missing_tables:
        err_msg = f"Database initialization failed. Missing required tables: {missing_tables}"
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    logger.info("Database schema initialized and verified successfully.")

    # Seed default identities referenced by agent tooling (idempotent).
    seed_default_identities(engine)


def seed_default_identities(engine: Engine) -> None:
    """
    Seed the default project and user identities referenced by the agent tools.

    The agent tools fall back to fixed UUIDs (DEFAULT_PROJECT_ID / DEFAULT_USER_ID)
    when no explicit project or user context is provided. On fresh databases those
    rows do not exist, so foreign-key constraints reject the agent's writes. This
    seeding is idempotent and safe to run on every schema initialization.
    """
    from atlas_db.models.core import (
        Organization,
        OrganizationMember,
        Project,
        User,
        OrganizationRole,
    )

    with Session(engine) as session:
        org = session.get(Organization, DEFAULT_ORGANIZATION_ID)
        if org is None:
            session.add(
                Organization(
                    id=DEFAULT_ORGANIZATION_ID,
                    name="Atlas",
                    slug="atlas",
                )
            )

        project = session.get(Project, DEFAULT_PROJECT_ID)
        if project is None:
            session.add(
                Project(
                    id=DEFAULT_PROJECT_ID,
                    name="Default",
                    slug="default",
                    description="Default project used by Atlas agent tooling.",
                )
            )

        exec_project = session.get(Project, DEFAULT_EXECUTION_PROJECT_ID)
        if exec_project is None:
            session.add(
                Project(
                    id=DEFAULT_EXECUTION_PROJECT_ID,
                    name="Execution Default",
                    slug="execution-default",
                    description="Default project used by the Atlas execution engine.",
                )
            )

        user = session.get(User, DEFAULT_USER_ID)
        if user is None:
            session.add(
                User(
                    id=DEFAULT_USER_ID,
                    email="agent@atlas.local",
                    full_name="Atlas Agent",
                    is_active=True,
                    is_verified=True,
                )
            )

        exec_user = session.get(User, DEFAULT_EXECUTION_USER_ID)
        if exec_user is None:
            session.add(
                User(
                    id=DEFAULT_EXECUTION_USER_ID,
                    email="execution-agent@atlas.local",
                    full_name="Atlas Execution Agent",
                    is_active=True,
                    is_verified=True,
                )
            )

        for member_id, member_user_id in (
            (DEFAULT_USER_ID, DEFAULT_USER_ID),
            (DEFAULT_EXECUTION_USER_ID, DEFAULT_EXECUTION_USER_ID),
        ):
            member = session.get(OrganizationMember, member_id)
            if member is None:
                session.add(
                    OrganizationMember(
                        id=member_id,
                        user_id=member_user_id,
                        organization_id=DEFAULT_ORGANIZATION_ID,
                        role=OrganizationRole.ADMIN,
                    )
                )

        try:
            session.commit()
        except Exception as e:
            session.rollback()
            logger.warning(f"Default identity seeding skipped (already present?): {e}")
