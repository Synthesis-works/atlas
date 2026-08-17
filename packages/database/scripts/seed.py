import os

from atlas_db.models.core import (
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    Project,
    User,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DEMO_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$Gdesz3DdjBSFPJHo+2/tuQ"
    "$DPrwn1ucpjF244zJt7DfdLLeUzcbalm7Dktn3TBXCCE"
)


def main():
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/atlas")

    engine = create_engine(db_url)
    print("Starting database seeding...")

    with Session(engine) as session:
        if session.query(User).filter(User.email == "demo@atlas.val").first():
            print("Seed already applied (demo@atlas.val present); skipping.")
            return

        # Create an Organization
        org = Organization(name="Atlas Development Team", slug="atlas-dev")
        session.add(org)
        session.commit()

        # Create a User
        admin_user = User(
            email="admin@atlas.local",
            full_name="Atlas Admin",
            org_id=org.id,
            is_active=True,
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$g4pnVKod3E0CzEDKN26z+g$UicSqlEoaoTeYZp8bM7erzPSnkwOs/pHEMucZVQXfw8",
        )
        session.add(admin_user)
        session.commit()

        # Create the demo user the frontend auto-login relies on
        # (demo@atlas.val / password123). Without this user every browser
        # session fails re-auth and all authenticated API calls return 401.
        demo_user = User(
            email="demo@atlas.val",
            full_name="Demo User",
            org_id=org.id,
            password_hash=DEMO_PASSWORD_HASH,
            is_active=True,
            is_verified=True,
        )
        session.add(demo_user)
        session.commit()

        session.add(
            OrganizationMember(
                user_id=demo_user.id,
                organization_id=org.id,
                role=OrganizationRole.ADMIN,
                status=MembershipStatus.ACTIVE,
            )
        )
        session.commit()

        # Create a Project
        project = Project(
            name="Demo Project",
            slug="demo-project",
            description="A sample project for development and testing",
            org_id=org.id,
        )
        session.add(project)
        session.commit()

        print(f"Seeded Organization: {org.name} ({org.id})")
        print(f"Seeded User: {admin_user.email} ({admin_user.id})")
        print(f"Seeded User: {demo_user.email} ({demo_user.id})")
        print(f"Seeded Project: {project.name} ({project.id})")

    print("Database seeding completed.")


if __name__ == "__main__":
    main()
