"""
One-time migration: copy everything out of the SQLite demo database
(gmpdoctrack.db) into your production SQL Server database.

WHEN TO USE THIS
    You started out running the app in demo mode (SQLite), entered some
    real data you don't want to lose, and have now set up SQL Server
    following the installation guide. This script copies every row across,
    exactly once, preserving all IDs and relationships (which document is
    in which box, which user issued which copy, the full audit trail,
    etc.) so nothing has to be re-entered by hand.

WHO SHOULD RUN THIS, AND HOW
    Run this ONCE, from the machine that has both the SQLite file and
    network access to SQL Server. Use an account with db_owner rights on
    the SQL Server database for this — NOT the restricted svc_gmpdoctrack
    application account described in the installation guide. This script
    needs to temporarily allow inserting specific ID numbers (called
    "IDENTITY_INSERT" in SQL Server), which requires more permission than
    the app itself normally has. Once migration is done, the app goes
    back to using its normal restricted account for everyday use — this
    script does not change that.

BEFORE YOU RUN IT
    1. Make sure you have already run schema_sqlserver.sql against an
       EMPTY SQL Server database (Part 4 of the installation guide). This
       script only copies DATA — it does not create tables.
    2. Set these values (see the installation guide, Part 6, for the
       exact format — using an account with db_owner rights, not the
       app's restricted svc_gmpdoctrack account):

           SOURCE_SQLITE_PATH   — path to your gmpdoctrack.db file
                                  (default: ./gmpdoctrack.db)

           Then EITHER (recommended — handles any password character
           with no manual encoding):
               DEST_DB_SERVER, DEST_DB_NAME, DEST_DB_USER, DEST_DB_PASSWORD
           OR (older single-string style — if your password contains
           @ : / # or %, you must percent-encode those characters
           yourself first):
               DEST_DATABASE_URL — e.g.
               mssql+pyodbc://YourAdminLogin:YourPassword@YOUR_SERVER/GMPDocTrack?driver=ODBC+Driver+17+for+SQL+Server

    3. Run it first with --dry-run to preview exactly what it will do
       without changing anything:

           python migrate_sqlite_to_sqlserver.py --dry-run

    4. If that looks right, run it for real:

           python migrate_sqlite_to_sqlserver.py

WHAT IT WON'T DO
    - It refuses to run against a destination table that already has data
      in it, to avoid creating duplicates. If you need to re-run this
      after a partial failure, see the printed error message for guidance.
    - It does not delete or modify your original gmpdoctrack.db file.
    - It does not touch the application's normal database-security setup
      (the DENY rules on the audit trail) — those apply to the app's
      regular svc_gmpdoctrack account, not to whatever admin account you
      use to run this one-time script.
"""
import argparse
import os
import sys

from sqlalchemy import create_engine, text, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app.db_base import Base
from app import models  # noqa: registers all tables on Base.metadata


def _build_dest_url():
    explicit = os.environ.get("DEST_DATABASE_URL")
    if explicit:
        return explicit
    dest_server = os.environ.get("DEST_DB_SERVER")
    if dest_server:
        url = URL.create(
            "mssql+pyodbc",
            username=os.environ.get("DEST_DB_USER", ""),
            password=os.environ.get("DEST_DB_PASSWORD", ""),
            host=dest_server,
            database=os.environ.get("DEST_DB_NAME", "GMPDocTrack"),
            query={"driver": os.environ.get("DEST_DB_DRIVER", "ODBC Driver 17 for SQL Server")},
        )
        return url.render_as_string(hide_password=False)
    return None


def get_engines():
    source_path = os.environ.get("SOURCE_SQLITE_PATH", "./gmpdoctrack.db")
    if not os.path.exists(source_path):
        print(f"ERROR: source SQLite file not found at '{source_path}'.")
        print("Set SOURCE_SQLITE_PATH to the correct path and try again.")
        sys.exit(1)

    dest_url = _build_dest_url()
    if not dest_url:
        print("ERROR: destination database settings are not set.")
        print("Set either DEST_DB_SERVER (+ DEST_DB_NAME/DEST_DB_USER/DEST_DB_PASSWORD)")
        print("or DEST_DATABASE_URL first — see the comment at the top of this file.")
        sys.exit(1)

    source_engine = create_engine(f"sqlite:///{source_path}")
    dest_engine = create_engine(dest_url)
    return source_engine, dest_engine


def table_row_count(engine, table):
    with engine.connect() as conn:
        result = conn.execute(select(table).limit(1))
        first_check = result.first()
        if first_check is None:
            return 0
        # cheap existence check above; get a real count only if non-empty
        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table.name}"))
        return count_result.scalar()


def has_single_integer_identity_pk(table):
    pk_cols = list(table.primary_key.columns)
    if len(pk_cols) != 1:
        return None
    col = pk_cols[0]
    if col.autoincrement in (True, "auto") and str(col.type).upper().startswith("INTEGER"):
        return col.name
    return None


def copy_table(source_engine, dest_engine, table, dry_run):
    with source_engine.connect() as sconn:
        rows = [dict(r._mapping) for r in sconn.execute(select(table))]

    if not rows:
        print(f"  {table.name}: 0 rows in source — nothing to copy.")
        return 0, 0

    if dry_run:
        print(f"  {table.name}: would copy {len(rows)} row(s).")
        return len(rows), 0

    identity_col = has_single_integer_identity_pk(table)
    is_mssql = dest_engine.dialect.name == "mssql"

    with dest_engine.begin() as dconn:
        if identity_col and is_mssql:
            dconn.execute(text(f"SET IDENTITY_INSERT {table.name} ON"))
        try:
            # documents.superseded_document_id is self-referencing: insert
            # with it nulled out first, restore it in a second pass after
            # every row exists, so the FK never points at a row that
            # hasn't been inserted yet.
            deferred_self_refs = []
            if table.name == "documents":
                for r in rows:
                    if r.get("superseded_document_id") is not None:
                        deferred_self_refs.append((r["id"], r["superseded_document_id"]))
                        r["superseded_document_id"] = None

            dconn.execute(table.insert(), rows)

            for doc_id, superseded_id in deferred_self_refs:
                dconn.execute(
                    table.update()
                    .where(table.c.id == doc_id)
                    .values(superseded_document_id=superseded_id)
                )
        finally:
            if identity_col and is_mssql:
                dconn.execute(text(f"SET IDENTITY_INSERT {table.name} OFF"))

    dest_count = table_row_count(dest_engine, table)
    print(f"  {table.name}: copied {len(rows)} row(s), destination now has {dest_count}.")
    return len(rows), dest_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="Preview what would be copied without writing anything.")
    parser.add_argument("--force", action="store_true",
                         help="Proceed even if a destination table already has data "
                              "(existing rows are left alone; new rows are added on top — "
                              "only use this if you know exactly why you need to).")
    args = parser.parse_args()

    source_engine, dest_engine = get_engines()

    print("=" * 70)
    print("GMP Document Tracking System — SQLite to SQL Server Migration")
    print("=" * 70)
    print(f"Source (SQLite):      {source_engine.url}")
    print(f"Destination (SQL Server): {dest_engine.url.render_as_string(hide_password=True)}")
    print(f"Mode: {'DRY RUN — nothing will be written' if args.dry_run else 'LIVE — data will be written'}")
    print()

    # Safety check: refuse to touch a destination that already has data,
    # unless the person explicitly passed --force.
    if not args.dry_run and not args.force:
        non_empty = []
        for table in Base.metadata.sorted_tables:
            count = table_row_count(dest_engine, table)
            if count > 0:
                non_empty.append((table.name, count))
        if non_empty:
            print("STOPPED: the destination database already has data in these tables:")
            for name, count in non_empty:
                print(f"  - {name}: {count} row(s)")
            print()
            print("Refusing to continue, to avoid creating duplicates.")
            print("If you're certain you want to proceed anyway (e.g. retrying")
            print("after a partial failure), re-run with --force.")
            sys.exit(1)

    print("Copying tables in dependency order (parent tables before the")
    print("child tables that reference them)...")
    print()

    summary = []
    for table in Base.metadata.sorted_tables:
        source_count, dest_count = copy_table(source_engine, dest_engine, table, args.dry_run)
        summary.append((table.name, source_count, dest_count))

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Table':<30} {'Source rows':>12} {'Destination rows':>18}")
    all_matched = True
    for name, source_count, dest_count in summary:
        if not args.dry_run and source_count != dest_count:
            all_matched = False
        marker = "" if args.dry_run else ("  <-- MISMATCH" if source_count != dest_count else "")
        print(f"{name:<30} {source_count:>12} {dest_count:>18}{marker}")

    print()
    if args.dry_run:
        print("This was a dry run — nothing was written. Re-run without --dry-run")
        print("to actually perform the migration.")
    elif all_matched:
        print("SUCCESS: every table's row count matches between source and destination.")
        print("Your data has been copied. You can now view it in SSMS.")
    else:
        print("WARNING: some row counts did not match — see MISMATCH lines above.")
        print("Do not delete your original gmpdoctrack.db file until this is resolved.")


if __name__ == "__main__":
    main()
