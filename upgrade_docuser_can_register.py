"""
One-time upgrade for an EXISTING database: grants the Doc Cell User role
permission to register new documents (DOC_CREATE). Nothing else about
that role, or any other role, is touched.

Safe to run more than once — checks first, does nothing if already
granted.

USAGE
    Same connection settings as everything else:
        python upgrade_docuser_can_register.py
"""
from app.database import SessionLocal
from app.models import Role, Permission, RolePermission


def run():
    print("=" * 70)
    print("Granting DOC_CREATE to the DOCCELL_USER role")
    print("=" * 70)

    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.code == "DOCCELL_USER").first()
        if not role:
            print("DOCCELL_USER role not found — has this database been seeded yet?")
            return

        perm = db.query(Permission).filter(Permission.code == "DOC_CREATE").first()
        if not perm:
            print("DOC_CREATE permission not found in this database — that's unexpected;")
            print("this database may predate even the base permission set. Stopping.")
            return

        already_granted = db.query(RolePermission).filter(
            RolePermission.role_id == role.id, RolePermission.permission_id == perm.id
        ).first()

        if already_granted:
            print("DOCCELL_USER already has DOC_CREATE — nothing to do.")
        else:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            db.commit()
            print("Granted DOC_CREATE to DOCCELL_USER.")

        print()
        print("No other permission, for this role or any other, was changed.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
