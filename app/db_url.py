"""
Builds the database connection URL from environment variables.

Deliberately has NO side effects at import time (no engine creation, no
actual connection attempt) — this file exists separately from database.py
specifically so tools like test_db_connection.py can import and call
build_database_url() to see what the app WOULD connect to, without that
import itself trying to connect to anything and crashing before the tool
gets a chance to run its own diagnostics.
"""
import os
from sqlalchemy.engine import URL


def build_database_url() -> str:
    explicit_url = os.environ.get("DATABASE_URL")
    if explicit_url:
        return explicit_url

    db_server = os.environ.get("DB_SERVER")
    if db_server:
        driver = os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server")
        db_name = os.environ.get("DB_NAME", "GMPDocTrack")
        trusted = os.environ.get("DB_TRUSTED_CONNECTION", "").strip().lower() in ("yes", "true", "1")

        if trusted:
            # Windows Authentication: connects as whichever Windows account
            # is running this script right now — no username/password at
            # all. Useful for one-off admin tasks (like creating a table)
            # using your own already-elevated Windows/SSMS login, without
            # needing a separate SQL-authentication admin account to exist.
            url = URL.create(
                "mssql+pyodbc",
                host=db_server,
                database=db_name,
                query={"driver": driver, "trusted_connection": "yes"},
            )
        else:
            # Building the URL this way (via SQLAlchemy's URL.create, passing
            # the raw password as a plain Python string) means SQLAlchemy does
            # all necessary escaping internally — the password is never typed
            # into a URL string by a human, so there is nothing to encode and
            # nothing to get wrong, regardless of which special characters it
            # contains.
            db_user = os.environ.get("DB_USER", "svc_gmpdoctrack")
            db_password = os.environ.get("DB_PASSWORD", "")
            url = URL.create(
                "mssql+pyodbc",
                username=db_user,
                password=db_password,
                host=db_server,
                database=db_name,
                query={"driver": driver},
            )
        return url.render_as_string(hide_password=False)

    return "sqlite:///./gmpdoctrack.db"
