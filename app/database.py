"""
Database connection layer.

Demo/dev default: SQLite file (gmpdoctrack.db) so the app runs anywhere with
zero external dependencies.

Production, RECOMMENDED way — separate pieces, no manual encoding ever
needed: set these instead of DATABASE_URL. If your password contains
special characters like @ : / # % (very common in strong passwords), this
approach handles them correctly and automatically — you never have to
remember to encode anything.

    DB_SERVER=YOUR_SERVER_NAME          (e.g. . or COMPUTERNAME\\SQLEXPRESS)
    DB_NAME=GMPDocTrack
    DB_USER=svc_gmpdoctrack
    DB_PASSWORD=Your@Actual:Password#Here      <- typed exactly as-is, no encoding
    DB_DRIVER=ODBC Driver 17 for SQL Server

Production, ALTERNATIVE way — a single connection string. This still
works and is kept for backward compatibility, but if your password
contains any of the characters @ : / # % ? you MUST percent-encode them
yourself in this string (@ becomes %40, : becomes %3A, / becomes %2F, #
becomes %23, % becomes %25) or the connection will silently parse
incorrectly and fail with a confusing "server not found"-style error:

    DATABASE_URL=mssql+pyodbc://svc_gmpdoctrack:Your%40Password@YOUR_SERVER/GMPDocTrack?driver=ODBC+Driver+17+for+SQL+Server

If both are set, DATABASE_URL takes priority (assumed intentional if
someone has deliberately kept using it).

No other application code changes are required to switch — SQLAlchemy's
ORM layer abstracts the dialect, and all queries are parameterized (no
raw SQL string concatenation anywhere in this codebase), which is the
primary SQL-injection control required by Section 25/38 of the spec.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .db_url import build_database_url
from .db_base import Base  # re-exported here for backward compatibility —
                            # existing code doing `from .database import Base`
                            # keeps working unchanged.

DATABASE_URL = build_database_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
