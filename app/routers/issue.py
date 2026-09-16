import json
from datetime import datetime, date
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user, require_permission
from ..audit import log_audit
from ..models import DocumentCopy, IssueTransaction, ReturnTransaction, TransferTransaction, User, Position
from ..services.location import build_location_code, storage_hierarchy_json
from ..templating import templates

router = APIRouter()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/issued-documents")
def issued_documents(request: Request, db: Session = Depends(get_db),
                      user=Depends(require_permission("REPORTS_VIEW"))):
    """A consolidated list of every currently-issued document copy —
    who it's with, why, when it's due back, and whether it's overdue."""
    open_issues = (
        db.query(IssueTransaction)
        .filter(IssueTransaction.is_open == True)  # noqa: E712
        .order_by(IssueTransaction.issue_datetime.desc())
        .all()
    )
    today = date.today()
    return templates.TemplateResponse("issued_documents.html", {
        "request": request, "user": user, "issues": open_issues, "today": today,
    })


@router.get("/issue/{copy_id}")
def issue_form(copy_id: int, request: Request, db: Session = Depends(get_db),
                user=Depends(require_permission("DOC_ISSUE"))):
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    return templates.TemplateResponse("issue_form.html", {"request": request, "user": user, "copy": copy, "users": users})


@router.post("/issue/{copy_id}")
def issue_document(
    copy_id: int, request: Request, db: Session = Depends(get_db),
    user=Depends(require_permission("DOC_ISSUE")),
    issued_to_user_id: int = Form(...), purpose: str = Form(None),
    expected_return_date: date = Form(...),
):
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    if copy.copy_status != "AVAILABLE":
        # Server-side guard — never trust client state (Section 38)
        return templates.TemplateResponse("error.html", {
            "request": request, "user": user,
            "message": f"Copy is currently {copy.copy_status}, cannot be issued.",
        }, status_code=409)

    issued_to_user = db.query(User).filter(User.id == issued_to_user_id).first()

    txn = IssueTransaction(
        document_copy_id=copy.id, issued_to_user_id=issued_to_user_id, purpose=purpose,
        expected_return_date=expected_return_date, issued_by_user_id=user.id,
    )
    db.add(txn)
    copy.copy_status = "ISSUED"
    copy.current_custodian_user_id = issued_to_user_id
    db.commit()

    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="ISSUE", record_type="DocumentCopy", record_id=copy.id,
               old_value="AVAILABLE",
               new_value=f"ISSUED to {issued_to_user.full_name} ({issued_to_user.ad_username})",
               reason=purpose)
    return RedirectResponse(url=f"/documents/{copy.document_id}", status_code=303)


@router.get("/return/{copy_id}")
def return_form(copy_id: int, request: Request, db: Session = Depends(get_db),
                 user=Depends(require_permission("DOC_RETURN"))):
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    open_txn = db.query(IssueTransaction).filter(
        IssueTransaction.document_copy_id == copy_id, IssueTransaction.is_open == True  # noqa: E712
    ).first()
    return templates.TemplateResponse("return_form.html", {"request": request, "user": user, "copy": copy, "open_txn": open_txn})


@router.post("/return/{copy_id}")
def return_document(
    copy_id: int, request: Request, db: Session = Depends(get_db),
    user=Depends(require_permission("DOC_RETURN")),
    physical_condition: str = Form("Good"), remarks: str = Form(None),
):
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    open_txn = db.query(IssueTransaction).filter(
        IssueTransaction.document_copy_id == copy_id, IssueTransaction.is_open == True  # noqa: E712
    ).first()
    if not open_txn:
        return templates.TemplateResponse("error.html", {
            "request": request, "user": user, "message": "No open issue transaction found for this copy.",
        }, status_code=409)

    ret = ReturnTransaction(
        issue_transaction_id=open_txn.id, returned_by_user_id=open_txn.issued_to_user_id,
        received_by_user_id=user.id, physical_condition=physical_condition,
        returned_position_id=copy.current_position_id, remarks=remarks,
    )
    db.add(ret)
    open_txn.is_open = False
    open_txn.actual_return_datetime = datetime.utcnow()
    copy.copy_status = "AVAILABLE"
    copy.current_custodian_user_id = None
    db.commit()

    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="RETURN", record_type="DocumentCopy", record_id=copy.id,
               old_value=f"ISSUED to {open_txn.issued_to.full_name}", new_value="AVAILABLE", reason=remarks)
    return RedirectResponse(url=f"/documents/{copy.document_id}", status_code=303)


@router.get("/transfer/{copy_id}")
def transfer_form(copy_id: int, request: Request, db: Session = Depends(get_db),
                   user=Depends(require_permission("DOC_TRANSFER"))):
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    hierarchy = storage_hierarchy_json(db)
    return templates.TemplateResponse("transfer_form.html", {
        "request": request, "user": user, "copy": copy, "hierarchy_json": json.dumps(hierarchy),
    })


@router.post("/transfer/{copy_id}")
def transfer_document(
    copy_id: int, request: Request, db: Session = Depends(get_db),
    user=Depends(require_permission("DOC_TRANSFER")),
    new_position_id: int = Form(...), reason: str = Form(...),
):
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    old_position_id = copy.current_position_id

    txn = TransferTransaction(
        document_copy_id=copy.id, old_position_id=old_position_id, new_position_id=new_position_id,
        reason=reason, transferred_by_user_id=user.id,
    )
    db.add(txn)

    new_code = build_location_code(db, new_position_id)

    # Close out the prior open DocumentLocationHistory row (if any) and open
    # a new one, so the movement timeline on the document detail page shows
    # this transfer alongside issues/returns/status changes.
    from ..models import DocumentLocationHistory
    open_loc = (
        db.query(DocumentLocationHistory)
        .filter(DocumentLocationHistory.document_copy_id == copy.id, DocumentLocationHistory.effective_to.is_(None))
        .first()
    )
    if open_loc:
        open_loc.effective_to = datetime.utcnow()
    db.add(DocumentLocationHistory(document_copy_id=copy.id, position_id=new_position_id,
                                    location_code=new_code, changed_by=user.full_name, reason=reason))

    copy.current_position_id = new_position_id
    copy.current_location_code = new_code
    db.commit()

    # old_position_id is preserved on the TransferTransaction row forever —
    # history is never overwritten (Section 16).
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="TRANSFER", record_type="DocumentCopy", record_id=copy.id,
               old_value=str(old_position_id), new_value=new_code, reason=reason)
    return RedirectResponse(url=f"/documents/{copy.document_id}", status_code=303)
