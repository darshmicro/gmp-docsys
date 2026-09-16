import json
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user, require_permission
from ..audit import log_audit
from ..models import (
    Document, DocumentCopy, DocumentType, DocumentCategory, Department,
    IssueTransaction, TransferTransaction, DocumentLocationHistory, DocumentStatusHistory,
)
from ..services.location import full_location_breadcrumb, build_location_code, storage_hierarchy_json
from ..templating import templates

router = APIRouter()


def _ip(request: Request):
    return request.client.host if request.client else None


def _user_permission_codes(db, user) -> set[str]:
    from ..models import RolePermission, Permission
    role_ids = [r.id for r in user.roles]
    if not role_ids:
        return set()
    rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id.in_(role_ids))
        .all()
    )
    return {r[0] for r in rows}


@router.get("/documents")
def list_documents(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    docs = db.query(Document).filter(Document.is_active == True).order_by(Document.document_number).limit(200).all()  # noqa: E712
    return templates.TemplateResponse("documents_list.html", {"request": request, "user": user, "docs": docs})


@router.get("/documents/new")
def new_document_form(request: Request, db: Session = Depends(get_db),
                       user=Depends(require_permission("DOC_CREATE"))):
    types = db.query(DocumentType).filter(DocumentType.is_active == True).all()  # noqa: E712
    cats = db.query(DocumentCategory).filter(DocumentCategory.is_active == True).all()  # noqa: E712
    depts = db.query(Department).filter(Department.is_active == True).all()  # noqa: E712
    hierarchy = storage_hierarchy_json(db)
    return templates.TemplateResponse("document_form.html", {
        "request": request, "user": user, "types": types, "cats": cats, "depts": depts,
        "hierarchy_json": json.dumps(hierarchy),
    })


@router.post("/documents/new")
def create_document(
    request: Request, db: Session = Depends(get_db),
    user=Depends(require_permission("DOC_CREATE")),
    document_number: str = Form(...), title: str = Form(...),
    document_type_id: int = Form(...), department_id: int | None = Form(None),
    revision_number: str = Form("00"),
    position_id: int | None = Form(None), copy_number: str = Form("01"),
):
    doc = Document(document_number=document_number, title=title,
                    document_type_id=document_type_id, department_id=department_id,
                    revision_number=revision_number, created_by=user.full_name)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="CREATE", record_type="Document", record_id=doc.id,
               new_value=f"{document_number} rev {revision_number}: {title}")

    # Section 10/23: allow selecting the physical storage location for the
    # first copy right at registration time, instead of a separate step.
    if position_id:
        code = build_location_code(db, position_id)
        copy = DocumentCopy(document_id=doc.id, copy_number=copy_number,
                             current_position_id=position_id, current_location_code=code,
                             created_by=user.full_name)
        db.add(copy)
        db.flush()
        db.add(DocumentLocationHistory(document_copy_id=copy.id, position_id=position_id,
                                        location_code=code, changed_by=user.full_name,
                                        reason="Initial placement at registration"))
        db.commit()
        log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
                   module="Documents", action="CREATE", record_type="DocumentCopy", record_id=copy.id,
                   new_value=f"Copy {copy_number} placed at {code}")

    return RedirectResponse(url=f"/documents/{doc.id}", status_code=303)


@router.get("/documents/{document_id}/copies/new")
def new_copy_form(document_id: int, request: Request, db: Session = Depends(get_db),
                   user=Depends(require_permission("DOC_CREATE"))):
    doc = db.query(Document).filter(Document.id == document_id).first()
    hierarchy = storage_hierarchy_json(db)
    return templates.TemplateResponse("copy_form.html", {
        "request": request, "user": user, "doc": doc, "hierarchy_json": json.dumps(hierarchy),
    })


@router.post("/documents/{document_id}/copies/new")
def create_copy(document_id: int, request: Request, db: Session = Depends(get_db),
                 user=Depends(require_permission("DOC_CREATE")),
                 copy_number: str = Form(...), position_id: int | None = Form(None)):
    copy = DocumentCopy(document_id=document_id, copy_number=copy_number, created_by=user.full_name)
    if position_id:
        code = build_location_code(db, position_id)
        copy.current_position_id = position_id
        copy.current_location_code = code
    db.add(copy)
    db.commit()
    db.refresh(copy)
    if position_id:
        db.add(DocumentLocationHistory(document_copy_id=copy.id, position_id=position_id,
                                        location_code=copy.current_location_code, changed_by=user.full_name,
                                        reason="Initial placement"))
        db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="CREATE", record_type="DocumentCopy", record_id=copy.id,
               new_value=f"Copy {copy_number}" + (f" placed at {copy.current_location_code}" if position_id else ""))
    return RedirectResponse(url=f"/documents/{document_id}", status_code=303)


@router.get("/documents/{document_id}")
def document_detail(document_id: int, request: Request, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    copies = db.query(DocumentCopy).filter(DocumentCopy.document_id == document_id).all()

    breadcrumbs = {}
    for c in copies:
        if c.current_position_id:
            breadcrumbs[c.id] = full_location_breadcrumb(db, c.current_position_id)

    # Movement history timeline (Section 30): merge status/location/issue/transfer events
    history = []
    for sh in db.query(DocumentStatusHistory).filter(DocumentStatusHistory.document_id == document_id).all():
        history.append({"date": sh.change_datetime, "event": f"Status changed {sh.old_status} -> {sh.new_status}", "reason": sh.reason})
    for c in copies:
        for loc in db.query(DocumentLocationHistory).filter(DocumentLocationHistory.document_copy_id == c.id).all():
            history.append({"date": loc.effective_from, "event": f"Copy {c.copy_number} stored at {loc.location_code}", "reason": loc.reason})
        for it in db.query(IssueTransaction).filter(IssueTransaction.document_copy_id == c.id).all():
            history.append({"date": it.issue_datetime, "event": f"Copy {c.copy_number} issued to {it.issued_to.full_name}", "reason": it.purpose})
            if it.actual_return_datetime:
                history.append({"date": it.actual_return_datetime, "event": f"Copy {c.copy_number} returned", "reason": None})
        for tt in db.query(TransferTransaction).filter(TransferTransaction.document_copy_id == c.id).all():
            history.append({"date": tt.transfer_datetime, "event": f"Copy {c.copy_number} transferred", "reason": tt.reason})
    history.sort(key=lambda h: h["date"])

    perms = _user_permission_codes(db, user)

    return templates.TemplateResponse("document_detail.html", {
        "request": request, "user": user, "doc": doc, "copies": copies,
        "breadcrumbs": breadcrumbs, "history": history,
        "can_issue": "DOC_ISSUE" in perms, "can_request_issue": "DOC_ISSUE_REQUEST" in perms,
    })
