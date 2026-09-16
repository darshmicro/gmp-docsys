"""
Shows exactly which permissions each role has in whichever database this
Command Prompt window is currently pointed at (SQLite or SQL Server —
same connection rules as check_users.py). Use this any time a feature
that should be visible to a role isn't showing up, to see directly
whether the permission is actually granted, instead of guessing.

USAGE
    In the SAME window where you set DB_SERVER / DB_USER / DB_PASSWORD /
    DB_NAME (or nothing, for the local SQLite file):

        python check_permissions.py

    Or check just one role:

        python check_permissions.py VIEWER
"""
import sys

from app.db_url import build_database_url

url = build_database_url()

print("=" * 70)
print("WHICH DATABASE AM I ACTUALLY LOOKING AT?")
print("=" * 70)
if url.startswith("sqlite"):
    print(f"Currently pointed at: the LOCAL SQLITE FILE ({url.replace('sqlite:///', '')})")
else:
    from sqlalchemy.engine.url import make_url
    parsed = make_url(url)
    print(f"Currently pointed at: SQL SERVER — {parsed.host} / {parsed.database}")
print()

try:
    from app.database import SessionLocal
    from app.models import Role, Permission, RolePermission
except Exception as e:
    print(f"Could not even import the application's own database code: {e}")
    sys.exit(1)

db = SessionLocal()
try:
    roles = db.query(Role).order_by(Role.code).all()
except Exception as e:
    print(f"Could not connect / query: {e}")
    print()
    print("If you're trying to check SQL Server, run test_db_connection.py first.")
    sys.exit(1)

only_role = sys.argv[1].upper() if len(sys.argv) > 1 else None

if not roles:
    print("No roles found at all in this database. Has it been seeded yet?")
    print("Run: python -m app.seed")
    sys.exit(0)

print("-" * 70)
for role in roles:
    if only_role and role.code != only_role:
        continue
    perms = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role.id)
        .order_by(Permission.code)
        .all()
    )
    codes = [p[0] for p in perms]
    print(f"\n{role.code}  ({len(codes)} permission(s)):")
    if codes:
        for c in codes:
            print(f"  - {c}")
    else:
        print("  (none)")

print()
print("-" * 70)
if not only_role or only_role == "VIEWER":
    has_request = db.query(Permission).join(RolePermission, RolePermission.permission_id == Permission.id) \
        .join(Role, Role.id == RolePermission.role_id) \
        .filter(Role.code == "VIEWER", Permission.code == "DOC_ISSUE_REQUEST").first()
    if has_request:
        print("VIEWER already has DOC_ISSUE_REQUEST — the permission itself is fine.")
        print("If the button still isn't showing, the issue is likely something else —")
        print("see the checklist this was printed alongside.")
    else:
        print("VIEWER does NOT have DOC_ISSUE_REQUEST in this database.")
        print()
        print("This is almost certainly why the Viewer can't request an issue. Run:")
        print("  python upgrade_add_issue_requests.py")
        print("in THIS SAME window, then check again.")
