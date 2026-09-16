from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from .db_base import Base


def utcnow():
    return datetime.utcnow()


class TimestampMixin:
    created_by = Column(String(100), nullable=False, default="system")
    created_date = Column(DateTime, default=utcnow, nullable=False)
    modified_by = Column(String(100), nullable=True)
    modified_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


# ---------------------------------------------------------------- SECURITY --

class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)  # SYSADMIN, DOCCELL_ADMIN, DOCCELL_USER, VIEWER
    name = Column(String(100), nullable=False)
    description = Column(String(300))


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    module = Column(String(50), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    ad_domain = Column(String(50), nullable=True)
    ad_username = Column(String(100), unique=True, nullable=False)  # "DOMAIN\\jsmith" or "local:admin"
    full_name = Column(String(150), nullable=False)
    email = Column(String(150))
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    designation = Column(String(100))
    is_local_emergency_account = Column(Boolean, default=False)
    local_password_hash = Column(String(200), nullable=True)  # bcrypt hash; NEVER an AD password
    account_status = Column(String(20), default="ACTIVE")  # ACTIVE / DISABLED / LOCKED
    failed_login_count = Column(Integer, default=0)
    last_login_date = Column(DateTime, nullable=True)

    department = relationship("Department")
    roles = relationship("Role", secondary="user_roles")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    assigned_by = Column(String(100), nullable=False, default="system")
    assigned_date = Column(DateTime, default=utcnow)


# --------------------------------------------------------------- MASTER DATA --

class DocumentType(Base, TimestampMixin):
    __tablename__ = "document_types"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)


class DocumentCategory(Base, TimestampMixin):
    __tablename__ = "document_categories"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)


# ------------------------------------------------------------- STORAGE TREE --

class StorageRoom(Base, TimestampMixin):
    __tablename__ = "storage_rooms"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)   # DR-01
    name = Column(String(150), nullable=False)
    building = Column(String(100))
    floor = Column(String(50))
    area = Column(String(100))
    description = Column(String(300))
    responsible_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    status = Column(String(20), default="ACTIVE")
    remarks = Column(String(500))

    racks = relationship("Rack", back_populates="room")


class Rack(Base, TimestampMixin):
    __tablename__ = "racks"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("storage_rooms.id"), nullable=False)
    rack_number = Column(String(20), nullable=False)  # R01
    description = Column(String(200))
    rack_type = Column(String(50))
    status = Column(String(20), default="ACTIVE")
    remarks = Column(String(500))
    __table_args__ = (UniqueConstraint("room_id", "rack_number", name="uq_rack"),)

    room = relationship("StorageRoom", back_populates="racks")
    sub_racks = relationship("SubRack", back_populates="rack")


class SubRack(Base, TimestampMixin):
    __tablename__ = "sub_racks"
    id = Column(Integer, primary_key=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=False)
    sub_rack_number = Column(String(20), nullable=False)  # SR01
    capacity = Column(Integer)
    status = Column(String(20), default="ACTIVE")
    remarks = Column(String(500))
    __table_args__ = (UniqueConstraint("rack_id", "sub_rack_number", name="uq_subrack"),)

    rack = relationship("Rack", back_populates="sub_racks")
    shelves = relationship("Shelf", back_populates="sub_rack")


class Shelf(Base, TimestampMixin):
    __tablename__ = "shelves"
    id = Column(Integer, primary_key=True)
    sub_rack_id = Column(Integer, ForeignKey("sub_racks.id"), nullable=False)
    shelf_number = Column(String(20), nullable=False)  # S02
    capacity = Column(Integer)
    status = Column(String(20), default="ACTIVE")
    remarks = Column(String(500))
    __table_args__ = (UniqueConstraint("sub_rack_id", "shelf_number", name="uq_shelf"),)

    sub_rack = relationship("SubRack", back_populates="shelves")
    positions = relationship("Position", back_populates="shelf")


class Position(Base, TimestampMixin):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    shelf_id = Column(Integer, ForeignKey("shelves.id"), nullable=False)
    position_number = Column(String(20), nullable=False)  # P05
    location_code = Column(String(100), index=True)  # denormalized cache, e.g. DR01-R04-SR02-S03-P05
    status = Column(String(20), default="ACTIVE")
    remarks = Column(String(500))
    __table_args__ = (UniqueConstraint("shelf_id", "position_number", name="uq_position"),)

    shelf = relationship("Shelf", back_populates="positions")


class DocumentBox(Base, TimestampMixin):
    __tablename__ = "document_boxes"
    id = Column(Integer, primary_key=True)
    box_number = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    capacity = Column(Integer)
    current_document_count = Column(Integer, default=0)
    status = Column(String(20), default="ACTIVE")

    position = relationship("Position")


# ------------------------------------------------------------------ DOCUMENTS --

class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    document_number = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=False)
    document_category_id = Column(Integer, ForeignKey("document_categories.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    product_process = Column(String(150))
    revision_number = Column(String(20), default="00")
    effective_date = Column(Date, nullable=True)
    expiry_review_date = Column(Date, nullable=True)
    superseded_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    status = Column(String(20), default="ACTIVE")
    # ACTIVE, UNDER_REVIEW, SUPERSEDED, OBSOLETE, ARCHIVED, WITHDRAWN, MISSING

    __table_args__ = (UniqueConstraint("document_number", "revision_number", name="uq_doc_rev"),
                       Index("ix_documents_number", "document_number"),
                       Index("ix_documents_title", "title"),
                       Index("ix_documents_status", "status"))

    document_type = relationship("DocumentType")
    category = relationship("DocumentCategory")
    department = relationship("Department")
    copies = relationship("DocumentCopy", back_populates="document")


class DocumentCopy(Base, TimestampMixin):
    __tablename__ = "document_copies"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    copy_number = Column(String(20), nullable=False)
    controlled_status = Column(String(20), default="CONTROLLED")
    original_or_copy = Column(String(20), default="ORIGINAL")
    number_of_pages = Column(Integer)
    box_id = Column(Integer, ForeignKey("document_boxes.id"), nullable=True)
    current_position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)
    current_location_code = Column(String(100))
    copy_status = Column(String(20), default="AVAILABLE")  # AVAILABLE / ISSUED / ARCHIVED / MISSING
    current_custodian_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (UniqueConstraint("document_id", "copy_number", name="uq_doc_copy"),
                       Index("ix_doccopies_location_code", "current_location_code"),
                       Index("ix_doccopies_status", "copy_status"),
                       Index("ix_doccopies_box_id", "box_id"))

    document = relationship("Document", back_populates="copies")
    box = relationship("DocumentBox")
    current_position = relationship("Position")
    current_custodian = relationship("User")


class DocumentLocationHistory(Base):
    __tablename__ = "document_location_history"
    id = Column(Integer, primary_key=True)
    document_copy_id = Column(Integer, ForeignKey("document_copies.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    location_code = Column(String(100), nullable=False)
    effective_from = Column(DateTime, default=utcnow, nullable=False)
    effective_to = Column(DateTime, nullable=True)  # NULL = current
    changed_by = Column(String(100), nullable=False)
    reason = Column(String(300))


# -------------------------------------------------------------- TRANSACTIONS --

class IssueTransaction(Base):
    __tablename__ = "issue_transactions"
    id = Column(Integer, primary_key=True)
    document_copy_id = Column(Integer, ForeignKey("document_copies.id"), nullable=False)
    issued_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    purpose = Column(String(300))
    issue_datetime = Column(DateTime, default=utcnow, nullable=False)
    expected_return_date = Column(Date, nullable=False)
    actual_return_datetime = Column(DateTime, nullable=True)
    issued_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remarks = Column(String(500))
    is_open = Column(Boolean, default=True, nullable=False)

    document_copy = relationship("DocumentCopy")
    issued_to = relationship("User", foreign_keys=[issued_to_user_id])
    issued_by = relationship("User", foreign_keys=[issued_by_user_id])


class IssueRequest(Base):
    """A viewer's request to be issued a document copy, awaiting approval
    by someone who holds DOC_ISSUE_APPROVE (Doc Cell User/Admin, Sysadmin).
    On approval, a real IssueTransaction is created with issued_to_user_id
    set to the ORIGINAL REQUESTER — the approver never becomes the
    custodian themselves, they just authorize the issue."""
    __tablename__ = "issue_requests"
    id = Column(Integer, primary_key=True)
    document_copy_id = Column(Integer, ForeignKey("document_copies.id"), nullable=False)
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    purpose = Column(String(300))
    requested_date = Column(DateTime, default=utcnow, nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING / APPROVED / REJECTED
    decided_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_date = Column(DateTime, nullable=True)
    decision_reason = Column(String(300))
    resulting_issue_transaction_id = Column(Integer, ForeignKey("issue_transactions.id"), nullable=True)

    document_copy = relationship("DocumentCopy")
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    decided_by = relationship("User", foreign_keys=[decided_by_user_id])
    resulting_issue_transaction = relationship("IssueTransaction")


class ReturnTransaction(Base):
    __tablename__ = "return_transactions"
    id = Column(Integer, primary_key=True)
    issue_transaction_id = Column(Integer, ForeignKey("issue_transactions.id"), nullable=False)
    returned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    return_datetime = Column(DateTime, default=utcnow, nullable=False)
    received_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    physical_condition = Column(String(100))
    returned_position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    remarks = Column(String(500))


class TransferTransaction(Base):
    __tablename__ = "transfer_transactions"
    id = Column(Integer, primary_key=True)
    document_copy_id = Column(Integer, ForeignKey("document_copies.id"), nullable=False)
    old_position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    new_position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    reason = Column(String(300), nullable=False)
    transferred_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    transfer_datetime = Column(DateTime, default=utcnow, nullable=False)
    remarks = Column(String(500))


class DocumentStatusHistory(Base):
    __tablename__ = "document_status_history"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    old_status = Column(String(20))
    new_status = Column(String(20), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    change_datetime = Column(DateTime, default=utcnow, nullable=False)
    reason = Column(String(300))


# --------------------------------------------------------------- AUDIT TRAIL --

class AuditTrail(Base):
    """Append-only. No update/delete path exists anywhere in the app layer
    for this table — see app/audit.py. In production, also DENY UPDATE/DELETE
    on this table at the SQL Server grant level (see sql/schema_sqlserver.sql)."""
    __tablename__ = "audit_trail"
    id = Column(Integer, primary_key=True)
    event_datetime_utc = Column(DateTime, default=utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String(150))
    ip_address = Column(String(50))
    module = Column(String(50), nullable=False)
    record_type = Column(String(50))
    record_id = Column(String(50))
    action = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    reason = Column(String(500))

    __table_args__ = (
        Index("ix_audit_module_record", "module", "record_type", "record_id"),
        Index("ix_audit_date", "event_datetime_utc"),
        Index("ix_audit_user", "user_id"),
    )


class SystemConfig(Base):
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(500))
    description = Column(String(300))
    is_gmp_critical = Column(Boolean, default=False)
    modified_by = Column(String(100))
    modified_date = Column(DateTime)
