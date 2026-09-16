from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import require_permission
from ..models import AuditTrail
from ..templating import templates

router = APIRouter()


@router.get("/audit")
def audit_trail(request: Request, db: Session = Depends(get_db),
                 user=Depends(require_permission("AUDIT_VIEW"))):
    entries = db.query(AuditTrail).order_by(AuditTrail.event_datetime_utc.desc()).limit(500).all()
    return templates.TemplateResponse("audit.html", {"request": request, "user": user, "entries": entries})
