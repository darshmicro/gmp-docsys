"""
Creates the database tables (demo/dev only — production uses
sql/schema_sqlserver.sql run by a DBA) and seeds:
  - Roles + Permissions + RolePermission matrix (Section 5)
  - Departments, DocumentTypes, DocumentCategories
  - Sample storage hierarchy (Section 43)
  - Demo local users, one per role, for immediate testing
Run:  python -m app.seed

SAFE TO RUN MORE THAN ONCE, on a database in ANY partial state — every
single step below checks whether its own row already exists before
creating it, rather than assuming either "nothing exists yet" or
"everything from a previous run exists." This matters because real-world
partial states can come from more than one cause: a crash partway through
a previous seed run, or a targeted upgrade script (like
upgrade_add_issue_requests.py) having already created some of the newer
permissions before this ever ran. Checking each row individually, instead
of one all-or-nothing decision, handles every combination correctly.
"""
from datetime import datetime
from passlib.hash import bcrypt
from .database import Base, engine, SessionLocal
from .models import (
    Department, Role, Permission, RolePermission, User, UserRole,
    DocumentType, DocumentCategory, StorageRoom, Rack, SubRack, Shelf, Position,
)
from .services.location import refresh_position_cache

PERMISSIONS = [
    # code, name, module
    ("DOC_VIEW", "View documents", "Documents"),
    ("DOC_CREATE", "Register documents", "Documents"),
    ("DOC_EDIT", "Edit document master data", "Documents"),
    ("DOC_ISSUE", "Issue documents", "Documents"),
    ("DOC_ISSUE_REQUEST", "Request that a document be issued (needs approval)", "Documents"),
    ("DOC_ISSUE_APPROVE", "Approve or reject issue requests", "Documents"),
    ("DOC_RETURN", "Return documents", "Documents"),
    ("DOC_TRANSFER", "Transfer document location", "Documents"),
    ("DOC_STATUS_CHANGE", "Change document status", "Documents"),
    ("MASTER_VIEW", "View master data", "Master Data"),
    ("MASTER_EDIT", "Edit master data (storage hierarchy, types, depts)", "Master Data"),
    ("SEARCH", "Search documents", "Search"),
    ("REPORTS_VIEW", "View/export reports", "Reports"),
    ("AUDIT_VIEW", "View audit trail", "Audit"),
    ("USER_MANAGE", "Manage users and roles", "Administration"),
    ("CONFIG_MANAGE", "Manage system configuration", "Administration"),
]

ROLE_PERMS = {
    "SYSADMIN": [p[0] for p in PERMISSIONS],  # everything
    "DOCCELL_ADMIN": [
        "DOC_VIEW", "DOC_CREATE", "DOC_EDIT", "DOC_ISSUE", "DOC_ISSUE_APPROVE", "DOC_RETURN",
        "DOC_TRANSFER", "DOC_STATUS_CHANGE", "MASTER_VIEW", "MASTER_EDIT",
        "SEARCH", "REPORTS_VIEW",
    ],
    "DOCCELL_USER": [
        "DOC_VIEW", "DOC_CREATE", "DOC_ISSUE", "DOC_ISSUE_APPROVE", "DOC_RETURN",
        "SEARCH", "MASTER_VIEW", "REPORTS_VIEW",
    ],
    "VIEWER": ["DOC_VIEW", "DOC_ISSUE_REQUEST", "SEARCH", "MASTER_VIEW"],
}

DEMO_USERS = [
    ("local:sysadmin", "System Administrator", "sysadmin@company.local", "SYSADMIN", "ChangeMe123!"),
    ("local:docadmin", "Priya Sharma (Doc Cell Admin)", "docadmin@company.local", "DOCCELL_ADMIN", "ChangeMe123!"),
    ("local:docuser", "Arjun Rao (Doc Cell User)", "docuser@company.local", "DOCCELL_USER", "ChangeMe123!"),
    ("local:viewer", "Read Only Viewer", "viewer@company.local", "VIEWER", "ChangeMe123!"),
]


def _get_or_create_department(db, code, name):
    existing = db.query(Department).filter(Department.code == code).first()
    if existing:
        return existing, False
    dept = Department(code=code, name=name, created_by="seed")
    db.add(dept)
    db.flush()
    return dept, True


def _get_or_create_role(db, code):
    existing = db.query(Role).filter(Role.code == code).first()
    if existing:
        return existing, False
    role = Role(code=code, name=code.replace("_", " ").title(), created_by="seed")
    db.add(role)
    db.flush()
    return role, True


def _get_or_create_permission(db, code, name, module):
    existing = db.query(Permission).filter(Permission.code == code).first()
    if existing:
        return existing, False
    perm = Permission(code=code, name=name, module=module)
    db.add(perm)
    db.flush()
    return perm, True


def _ensure_role_permission(db, role_id, permission_id):
    existing = db.query(RolePermission).filter(
        RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
    ).first()
    if existing:
        return False
    db.add(RolePermission(role_id=role_id, permission_id=permission_id))
    return True


def _get_or_create_document_type(db, code, name):
    existing = db.query(DocumentType).filter(DocumentType.code == code).first()
    if existing:
        return existing, False
    dt = DocumentType(code=code, name=name, created_by="seed")
    db.add(dt)
    db.flush()
    return dt, True


def _get_or_create_document_category(db, code, name):
    existing = db.query(DocumentCategory).filter(DocumentCategory.code == code).first()
    if existing:
        return existing, False
    dc = DocumentCategory(code=code, name=name, created_by="seed")
    db.add(dc)
    db.flush()
    return dc, True


def _get_or_create_storage_room(db, code, name, building, floor, department_id):
    existing = db.query(StorageRoom).filter(StorageRoom.code == code).first()
    if existing:
        return existing, False
    room = StorageRoom(code=code, name=name, building=building, floor=floor,
                        responsible_department_id=department_id, created_by="seed")
    db.add(room)
    db.flush()
    return room, True


def _get_or_create_rack(db, room_id, rack_number):
    existing = db.query(Rack).filter(Rack.room_id == room_id, Rack.rack_number == rack_number).first()
    if existing:
        return existing, False
    rack = Rack(room_id=room_id, rack_number=rack_number, created_by="seed")
    db.add(rack)
    db.flush()
    return rack, True


def _get_or_create_sub_rack(db, rack_id, sub_rack_number):
    existing = db.query(SubRack).filter(
        SubRack.rack_id == rack_id, SubRack.sub_rack_number == sub_rack_number
    ).first()
    if existing:
        return existing, False
    sub_rack = SubRack(rack_id=rack_id, sub_rack_number=sub_rack_number, capacity=100, created_by="seed")
    db.add(sub_rack)
    db.flush()
    return sub_rack, True


def _get_or_create_shelf(db, sub_rack_id, shelf_number):
    existing = db.query(Shelf).filter(
        Shelf.sub_rack_id == sub_rack_id, Shelf.shelf_number == shelf_number
    ).first()
    if existing:
        return existing, False
    shelf = Shelf(sub_rack_id=sub_rack_id, shelf_number=shelf_number, capacity=50, created_by="seed")
    db.add(shelf)
    db.flush()
    return shelf, True


def _get_or_create_position(db, shelf_id, position_number):
    existing = db.query(Position).filter(
        Position.shelf_id == shelf_id, Position.position_number == position_number
    ).first()
    if existing:
        return existing, False
    pos = Position(shelf_id=shelf_id, position_number=position_number, created_by="seed")
    db.add(pos)
    db.flush()
    return pos, True


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Users already exist — skipping. Delete gmpdoctrack.db (or truncate the "
                  "tables on SQL Server) to reseed from scratch.")
            return

        created_counts = {"departments": 0, "roles": 0, "permissions": 0, "role_permissions": 0,
                           "document_types": 0, "document_categories": 0, "storage": 0}

        # --- Departments
        qa, created = _get_or_create_department(db, "QA", "Quality Assurance")
        created_counts["departments"] += created
        _, created = _get_or_create_department(db, "QC", "Quality Control")
        created_counts["departments"] += created
        _, created = _get_or_create_department(db, "PROD", "Production")
        created_counts["departments"] += created

        # --- Roles
        roles = {}
        for code in ROLE_PERMS:
            role, created = _get_or_create_role(db, code)
            roles[code] = role
            created_counts["roles"] += created

        # --- Permissions
        perms = {}
        for code, name, module in PERMISSIONS:
            perm, created = _get_or_create_permission(db, code, name, module)
            perms[code] = perm
            created_counts["permissions"] += created

        # --- Role <-> Permission grants
        for role_code, perm_codes in ROLE_PERMS.items():
            for pc in perm_codes:
                created = _ensure_role_permission(db, roles[role_code].id, perms[pc].id)
                created_counts["role_permissions"] += created
        db.flush()

        # --- Document types/categories
        for code, name in [("SOP", "Standard Operating Procedure"), ("FORM", "Form"),
                            ("POLICY", "Policy"), ("SPEC", "Specification"), ("PROTOCOL", "Protocol")]:
            _, created = _get_or_create_document_type(db, code, name)
            created_counts["document_types"] += created
        for code, name in [("QMS", "Quality Management System"), ("MFG", "Manufacturing"), ("LAB", "Laboratory")]:
            _, created = _get_or_create_document_category(db, code, name)
            created_counts["document_categories"] += created

        # --- Sample storage hierarchy (Section 43)
        dr01, created = _get_or_create_storage_room(db, "DR-01", "Document Storage Room 01",
                                                      "Main Building", "Ground Floor", qa.id)
        created_counts["storage"] += created
        dr02, created = _get_or_create_storage_room(db, "DR-02", "Document Storage Room 02",
                                                      "Main Building", "Ground Floor", qa.id)
        created_counts["storage"] += created

        position_ids = []
        for room, rack_numbers in [(dr01, ["R01", "R02", "R03"]), (dr02, ["R01", "R02"])]:
            for rn in rack_numbers:
                rack, created = _get_or_create_rack(db, room.id, rn)
                created_counts["storage"] += created
                for srn in ["SR01", "SR02", "SR03"]:
                    sub_rack, created = _get_or_create_sub_rack(db, rack.id, srn)
                    created_counts["storage"] += created
                    for sn in ["S01", "S02", "S03", "S04"]:
                        shelf, created = _get_or_create_shelf(db, sub_rack.id, sn)
                        created_counts["storage"] += created
                        for pn in ["P01", "P02", "P03"]:
                            pos, created = _get_or_create_position(db, shelf.id, pn)
                            created_counts["storage"] += created
                            position_ids.append(pos.id)
        db.commit()
        for pid in position_ids:
            refresh_position_cache(db, pid, commit=False)
        db.commit()

        print("Master data check complete — newly created this run:")
        for label, count in created_counts.items():
            print(f"  {label}: {count} new")

        # --- Demo users (LOCAL auth mode only — see app/auth.py for AD mode)
        # Hashing happens here, deliberately, as the LAST step: if bcrypt is
        # broken (see requirements.txt note), everything above this point —
        # roles, permissions, storage hierarchy — is still committed and
        # reusable on the next run once bcrypt is fixed, instead of being
        # silently thrown away.
        try:
            for username, full_name, email, role_code, pwd in DEMO_USERS:
                u = User(
                    ad_username=username, full_name=full_name, email=email,
                    department_id=qa.id, is_local_emergency_account=True,
                    local_password_hash=bcrypt.hash(pwd), created_by="seed",
                )
                db.add(u)
                db.flush()
                db.add(UserRole(user_id=u.id, role_id=roles[role_code].id, assigned_by="seed"))
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"\nERROR: failed to create demo users: {e}\n")
            print("Master data (roles/departments/storage) was still committed successfully.")
            print("This is almost always a bcrypt/passlib version mismatch. Run:")
            print("  pip install 'bcrypt==4.0.1' --force-reinstall")
            print("then re-run `python -m app.seed` — it will pick up where it left off.")
            raise

        print("\nSeed complete. Demo logins (username / password):")
        for username, *_rest, pwd in DEMO_USERS:
            print(f"  {username} / {pwd}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
