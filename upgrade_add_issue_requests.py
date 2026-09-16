"""
One-time upgrade: adds the Document Issue Request workflow (viewers
requesting a document be issued to them, Doc Cell staff approving or
rejecting that request) to an EXISTING database that already has real
data in it.

Safe to run more than once — every step checks first and skips anything
already present, so running it twice does nothing harmful the second
time.

WHAT THIS ADDS
  - A new table, issue_requests.
  - Two new permissions: DOC_ISSUE_REQUEST, DOC_ISSUE_APPROVE.
  - Grants DOC_ISSUE_REQUEST to the VIEWER role, and DOC_ISSUE_APPROVE to
    DOCCELL_USER, DOCCELL_ADMIN, and SYSADMIN (matching who can already
    issue documents directly).

USAGE
    Use the exact same connection settings you use for everything else —
    DB_SERVER/DB_NAME/DB_USER/DB_PASSWORD for SQL Server, or nothing set
    at all for the local SQLite file:

        python upgrade_add_issue_requests.py

    If you're on a brand NEW installation that hasn't been seeded yet,
    just run `python -m app.seed` instead — it already includes
    everything this script adds, so you don't need to run this too.
"""
from app.database import engine, SessionLocal
from app.db_base import Base
from app import models  # noqa: registers all tables, including the new one, on Base.metadata
from app.models import Permission, RolePermission, Role

NEW_PERMISSIONS = [
    ("DOC_ISSUE_REQUEST", "Request that a document be issued (needs approval)", "Documents"),
    ("DOC_ISSUE_APPROVE", "Approve or reject issue requests", "Documents"),
]

GRANTS = {
    "VIEWER": ["DOC_ISSUE_REQUEST"],
    "DOCCELL_USER": ["DOC_ISSUE_APPROVE"],
    "DOCCELL_ADMIN": ["DOC_ISSUE_APPROVE"],
    "SYSADMIN": ["DOC_ISSUE_REQUEST", "DOC_ISSUE_APPROVE"],
}


def run():
    print("=" * 70)
    print("Adding the Issue Request workflow to an existing database")
    print("=" * 70)

    print("\nStep 1: creating the issue_requests table if it doesn't exist yet...")
    Base.metadata.create_all(bind=engine)  # only creates tables that are missing — never touches existing ones
    print("Done — your existing tables and data were not touched.")

    db = SessionLocal()
    try:
        print("\nStep 2: adding new permissions if missing...")
        perm_objs = {}
        for code, name, module in NEW_PERMISSIONS:
            existing = db.query(Permission).filter(Permission.code == code).first()
            if existing:
                print(f"  {code}: already exists — skipping.")
                perm_objs[code] = existing
            else:
                p = Permission(code=code, name=name, module=module)
                db.add(p)
                db.flush()
                perm_objs[code] = p
                print(f"  {code}: created.")
        db.commit()

        print("\nStep 3: granting the new permissions to the right roles...")
        for role_code, perm_codes in GRANTS.items():
            role = db.query(Role).filter(Role.code == role_code).first()
            if not role:
                print(f"  Role {role_code} not found in this database — has it been seeded yet? Skipping.")
                continue
            for perm_code in perm_codes:
                perm = perm_objs[perm_code]
                already_granted = db.query(RolePermission).filter(
                    RolePermission.role_id == role.id, RolePermission.permission_id == perm.id
                ).first()
                if already_granted:
                    print(f"  {role_code} already has {perm_code} — skipping.")
                else:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                    print(f"  Granted {perm_code} to {role_code}.")
        db.commit()

        print("\n" + "=" * 70)
        print("Upgrade complete. Viewers can now request documents be issued to")
        print("them; Doc Cell staff can approve or reject those requests from the")
        print("new 'Issue Requests' page in the sidebar.")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    run()
