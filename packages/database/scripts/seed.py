import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from atlas_db.models.core import Organization, User, Project

async def main():
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/atlas")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    elif db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    print("Starting database seeding...")

    async with async_session() as session:
        # Create an Organization
        org = Organization(name="Atlas Development Team")
        session.add(org)
        await session.commit()
        
        # Create a User
        admin_user = User(
            email="admin@atlas.local",
            full_name="Atlas Admin",
            org_id=org.id,
            is_active=True
        )
        session.add(admin_user)
        await session.commit()

        # Create a Project
        project = Project(
            name="Demo Project",
            description="A sample project for development and testing",
            org_id=org.id
        )
        session.add(project)
        await session.commit()

        print(f"Seeded Organization: {org.name} ({org.id})")
        print(f"Seeded User: {admin_user.email} ({admin_user.id})")
        print(f"Seeded Project: {project.name} ({project.id})")

    print("Database seeding completed.")

if __name__ == "__main__":
    asyncio.run(main())
