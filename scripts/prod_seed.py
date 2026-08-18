"""
Idempotent production seed runner for Atlas.

Runs the three seed layers in dependency order against the database
configured by DATABASE_URL:

  1. Core seed (packages/database/scripts/seed.py)
     Organization, admin user, demo user (demo@atlas.val), demo project.
  2. Demo seed (seed_demo.py)
     Demo benchmarks, datasets, execution history, leaderboards, reports.
  3. Default identity seeding (atlas_db.core.initialize.seed_default_identities)
     Fixed-UUID organization/project/users referenced by agent tooling and the
     execution engine. PostgreSQL enforces the foreign keys these rows back,
     and the dev-only auto-initialization path does not run in production.

Every step is guarded so re-running is safe (no-op when already applied).

Usage:
    DATABASE_URL=postgresql://... python scripts/prod_seed.py
"""

import os
import runpy
import sys

REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "database"))


def _step1_core_seed() -> None:
    print("[1/3] Running core seed (organization, users, project)...")
    runpy.run_path(
        os.path.join(REPO_ROOT, "packages", "database", "scripts", "seed.py"),
        run_name="__main__",
    )


def _step2_demo_seed() -> None:
    print("[2/3] Running demo seed (benchmarks, datasets, history)...")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from atlas_db.models.authoring import Benchmark

    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as session:
        if session.query(Benchmark).first():
            print("Demo seed already applied (benchmarks exist); skipping.")
            return
    runpy.run_path(os.path.join(REPO_ROOT, "seed_demo.py"), run_name="__main__")


def _step3_default_identities() -> None:
    print("[3/3] Seeding default identities required by PostgreSQL foreign keys...")
    from atlas_db.core.initialize import seed_default_identities
    from atlas_db.core.session import engine

    seed_default_identities(engine)


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL is required.")
        return 1

    _step1_core_seed()
    _step2_demo_seed()
    _step3_default_identities()

    print("=" * 60)
    print("Production seed complete. Re-running is safe (idempotent).")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
