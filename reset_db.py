import sqlalchemy
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:postgres@localhost:5432/atlas')
with engine.connect() as conn:
    conn.execute(sqlalchemy.text('DROP SCHEMA public CASCADE; CREATE SCHEMA public;'))
    conn.commit()
