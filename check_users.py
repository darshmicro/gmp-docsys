"""
Shows exactly which database the application is CURRENTLY configured to
use in this Command Prompt window, and lists every user account found
there. Run this any time you're not 100% sure whether you're looking at
SQL Server or the local SQLite file — it removes all doubt in one step.

USAGE
    In the SAME Command Prompt window where you set DB_SERVER / DB_USER /
    DB_PASSWORD / DB_NAME (or DATABASE_URL), run:

        python check_users.py
"""
import sys

from app.db_url import build_database_url

url = build_database_url()

print("=" * 70)
print("WHICH DATABASE AM I ACTUALLY LOOKING AT?")
print("=" * 70)

if url.startswith("sqlite"):
    print("Currently pointed at: the LOCAL SQLITE FILE (not SQL Server)")
    print(f"  File: {url.replace('sqlite:///', '')}")
    print()
    print("If you meant to check SQL Server, your DB_SERVER (or DATABASE_URL)")
    print("setting is not active in this window. Set it again, in THIS SAME")
    print("window, then run this script again — for example:")
    print("  set DB_SERVER=YOUR_SERVER_NAME")
    print("  set DB_NAME=GMPDocTrack")
    print("  set DB_USER=svc_gmpdoctrack")
    print("  set DB_PASSWORD=YourRealPassword")
    print("  python check_users.py")
else:
    from sqlalchemy.engine.url import make_url
    parsed = make_url(url)
    print(f"Currently pointed at: SQL SERVER")
    print(f"  Server:   {parsed.host}")
    print(f"  Database: {parsed.database}")
    print(f"  Username: {parsed.username}")

print()
print("-" * 70)
print("Connecting and listing users found there...")
print("-" * 70)

try:
    from app.database import SessionLocal
    from app.models import User
    db = SessionLocal()
    users = db.query(User).all()
    if not users:
        print("Connected successfully, but found ZERO users in this database.")
        print()
        print("If this says SQL Server above: run 'python -m app.seed' in THIS")
        print("SAME window (don't close it first) to create the demo accounts here.")
        print()
        print("If this says the local SQLite file above, but you expected SQL")
        print("Server: your DB_SERVER setting isn't active in this window — see")
        print("the note above.")
    else:
        print(f"Found {len(users)} user(s):")
        for u in users:
            roles = ", ".join(r.code for r in u.roles) or "(no role assigned)"
            print(f"  - {u.ad_username:25s} | {u.full_name:30s} | roles: {roles}")
except Exception as e:
    print(f"Could not connect: {e}")
    print()
    print("If you're trying to check SQL Server, run test_db_connection.py")
    print("first to pin down the connection problem before checking users.")
    sys.exit(1)
