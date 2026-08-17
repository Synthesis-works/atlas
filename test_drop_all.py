import os
import sqlalchemy
from sqlalchemy import create_engine
import atlas_db.models
from atlas_db.core.base import Base

DB_URL = "postgresql://postgres:postgres@localhost:5432/atlas"
engine = create_engine(DB_URL)

print("Running create_all...")
Base.metadata.create_all(bind=engine)

print("Running drop_all...")
Base.metadata.drop_all(bind=engine)

print("Success!")
