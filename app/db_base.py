"""
The SQLAlchemy declarative Base, kept in its own file with zero side
effects (no engine creation, no connection attempts).

Why this is separate from database.py: models.py needs Base to define
tables, and standalone tools (test_db_connection.py, the migration
script) need Base's metadata to know what tables exist — but neither of
those should have to trigger the *main application's* database engine
creation just to get it. Importing from here instead of database.py
means "give me the table definitions" and "connect to the app's
configured database" are two independent actions, not bundled together.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
