import os
import sys

sys.path.insert(0, os.path.abspath("packages/database"))
from apps.backend.config import settings
from sqlalchemy import create_engine
from atlas_db.core.base import Base
# Import all models to ensure they are registered
from atlas_db.models.billing import *
from atlas_db.models.core import *
from atlas_db.models.execution import *
from atlas_db.models.reports import *
from atlas_db.models.system import *

def main():
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    print("Database schema created successfully.")

if __name__ == "__main__":
    main()
