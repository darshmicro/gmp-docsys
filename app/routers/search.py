from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user, require_permission
from ..models import Document, DocumentCopy, DocumentType, Department
from ..templating import templates

router = APIRouter()


@router.get("/search")
def search(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    department_id: int | None = None,
    document_type_id: int | None = None,
    location_code: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("SEARCH")),
):
    query = db.query(Document).filter(Document.is_active == True)  # noqa: E712

    if q:
        like = f"%{q}%"
        query = query.filter((Document.document_number.ilike(like)) | (Document.title.ilike(like)))
    if status:
        query = query.filter(Document.status == status)
    if department_id:
        query = query.filter(Document.department_id == department_id)
    if document_type_id:
        query = query.filter(Document.document_type_id == document_type_id)

    results = query.limit(100).all()

    if location_code:
        # Search by physical location code across copies, then map back to documents
        like = f"%{location_code}%"
        copy_matches = db.query(DocumentCopy).filter(DocumentCopy.current_location_code.ilike(like)).all()
        doc_ids = {c.document_id for c in copy_matches}
        results = [d for d in results if d.id in doc_ids] if q or status or department_id or document_type_id \
            else db.query(Document).filter(Document.id.in_(doc_ids)).all()

    types = db.query(DocumentType).filter(DocumentType.is_active == True).all()  # noqa: E712
    depts = db.query(Department).filter(Department.is_active == True).all()  # noqa: E712

    return templates.TemplateResponse("search.html", {
        "request": request, "user": user, "results": results, "types": types, "depts": depts,
        "q": q, "status": status,
    })
