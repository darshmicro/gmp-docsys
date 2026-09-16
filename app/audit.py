"""
Central, single write-path for the GMP audit trail.

Design intent (Section 17 / ALCOA+):
  - This is the ONLY function in the codebase permitted to INSERT into
    AuditTrail. No route or service ever writes to that table directly, and
    nothing in the app ever UPDATEs or DELETEs a row in it.
  - event_datetime_utc always comes from the application/database server
    clock (utcnow()), never from client input, satisfying "Contemporaneous".
  - Every call captures Who (user), What (action + old/new value), When
    (server timestamp), Where (module/record), Why (reason) as required by
    Section 42.
"""
from sqlalchemy.orm import Session
from .models import AuditTrail


def log_audit(
    db: Session,
    *,
    user_id: int | None,
    user_name: str,
    ip_address: str | None,
    module: str,
    action: str,
    record_type: str | None = None,
    record_id: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
    commit: bool = True,
) -> AuditTrail:
    entry = AuditTrail(
        user_id=user_id,
        user_name=user_name,
        ip_address=ip_address,
        module=module,
        action=action,
        record_type=record_type,
        record_id=str(record_id) if record_id is not None else None,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
