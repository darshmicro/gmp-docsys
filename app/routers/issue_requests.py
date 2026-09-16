from datetime import datetime, date
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user, require_permission
from ..audit import log_audit
from ..models import DocumentCopy, IssueRequest, IssueTransaction, User
from ..templating import templates

router = APIRouter()


def _ip(request: Request):
    return request.client.host if request.client else None


def _user_permission_codes(db: Session, user) -> set[str]:
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


def _create_issue_request(db: Session, user, copy_id: int, purpose: str | None):
    """Shared validation + creation logic, used by both the per-document
    'Request Issue' button and the central picker on the Issue Requests
    page. Returns (issue_request_or_none, error_message_or_none)."""
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    if not copy:
        return None, "That document copy could not be found."
    if copy.copy_status != "AVAILABLE":
        return None, f"Copy is currently {copy.copy_status} — a request can only be made for an available copy."

    existing_pending = db.query(IssueRequest).filter(
        IssueRequest.document_copy_id == copy_id,
        IssueRequest.requested_by_user_id == user.id,
        IssueRequest.status == "PENDING",
    ).first()
    if existing_pending:
        return None, "You already have a pending request for this copy — wait for it to be approved or rejected."

    req = IssueRequest(document_copy_id=copy_id, requested_by_user_id=user.id, purpose=purpose)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req, None


@router.get("/issue-requests/new")
def new_issue_request_form(request: Request, db: Session = Depends(get_db),
                            user=Depends(require_permission("DOC_ISSUE_REQUEST"))):
    """The central entry point: pick any available document copy from a
    list and request it, without needing to browse to that document's own
    detail page first."""
    available_copies = (
        db.query(DocumentCopy)
        .filter(DocumentCopy.copy_status == "AVAILABLE")
        .join(DocumentCopy.document)
        .order_by(DocumentCopy.document_id)
        .all()
    )
    return templates.TemplateResponse("issue_request_new.html", {
        "request": request, "user": user, "available_copies": available_copies, "error": None,
    })


@router.post("/issue-requests/new")
def new_issue_request_submit(request: Request, db: Session = Depends(get_db),
                              user=Depends(require_permission("DOC_ISSUE_REQUEST")),
                              document_copy_id: int = Form(...), purpose: str = Form(None)):
    req, error = _create_issue_request(db, user, document_copy_id, purpose)
    if error:
        available_copies = (
            db.query(DocumentCopy).filter(DocumentCopy.copy_status == "AVAILABLE")
            .join(DocumentCopy.document).order_by(DocumentCopy.document_id).all()
        )
        return templates.TemplateResponse("issue_request_new.html", {
            "request": request, "user": user, "available_copies": available_copies, "error": error,
        }, status_code=409)

    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="ISSUE_REQUEST_CREATED", record_type="IssueRequest", record_id=req.id,
               new_value=f"Requested by {user.full_name} for copy {document_copy_id}", reason=purpose)
    return RedirectResponse(url="/issue-requests", status_code=303)


@router.get("/documents/{document_id}/copies/{copy_id}/request-issue")
def request_issue_form(document_id: int, copy_id: int, request: Request, db: Session = Depends(get_db),
                        user=Depends(require_permission("DOC_ISSUE_REQUEST"))):
    copy = db.query(DocumentCopy).filter(DocumentCopy.id == copy_id).first()
    return templates.TemplateResponse("request_issue_form.html", {"request": request, "user": user, "copy": copy})


@router.post("/documents/{document_id}/copies/{copy_id}/request-issue")
def request_issue_submit(document_id: int, copy_id: int, request: Request, db: Session = Depends(get_db),
                          user=Depends(require_permission("DOC_ISSUE_REQUEST")),
                          purpose: str = Form(None)):
    req, error = _create_issue_request(db, user, copy_id, purpose)
    if error:
        return templates.TemplateResponse("error.html", {
            "request": request, "user": user, "message": error,
        }, status_code=409)

    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="ISSUE_REQUEST_CREATED", record_type="IssueRequest", record_id=req.id,
               new_value=f"Requested by {user.full_name} for copy {copy_id}", reason=purpose)
    return RedirectResponse(url="/issue-requests", status_code=303)


@router.get("/issue-requests")
def list_issue_requests(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Doc Cell staff (DOC_ISSUE_APPROVE) see every request, with
    Approve/Reject actions on pending ones. Everyone else (e.g. a Viewer
    with only DOC_ISSUE_REQUEST) sees just their own requests, read-only."""
    perms = _user_permission_codes(db, user)
    can_approve = "DOC_ISSUE_APPROVE" in perms
    can_request = "DOC_ISSUE_REQUEST" in perms

    query = db.query(IssueRequest).order_by(IssueRequest.requested_date.desc())
    if not can_approve:
        query = query.filter(IssueRequest.requested_by_user_id == user.id)
    requests_list = query.all()

    return templates.TemplateResponse("issue_requests_list.html", {
        "request": request, "user": user, "requests_list": requests_list,
        "can_approve": can_approve, "can_request": can_request,
    })


@router.post("/issue-requests/{request_id}/approve")
def approve_issue_request(request_id: int, request: Request, db: Session = Depends(get_db),
                           user=Depends(require_permission("DOC_ISSUE_APPROVE")),
                           expected_return_date: date = Form(...)):
    req = db.query(IssueRequest).filter(IssueRequest.id == request_id).first()
    if req.status != "PENDING":
        return templates.TemplateResponse("error.html", {
            "request": request, "user": user,
            "message": f"This request is already {req.status} and can't be approved again.",
        }, status_code=409)

    copy = db.query(DocumentCopy).filter(DocumentCopy.id == req.document_copy_id).first()
    if copy.copy_status != "AVAILABLE":
        return templates.TemplateResponse("error.html", {
            "request": request, "user": user,
            "message": f"Copy is currently {copy.copy_status} — cannot approve this request right now.",
        }, status_code=409)

    # The requester becomes the custodian — the approver just authorizes it.
    txn = IssueTransaction(
        document_copy_id=copy.id, issued_to_user_id=req.requested_by_user_id, purpose=req.purpose,
        expected_return_date=expected_return_date, issued_by_user_id=user.id, approved_by_user_id=user.id,
    )
    db.add(txn)
    copy.copy_status = "ISSUED"
    copy.current_custodian_user_id = req.requested_by_user_id
    db.flush()

    req.status = "APPROVED"
    req.decided_by_user_id = user.id
    req.decided_date = datetime.utcnow()
    req.resulting_issue_transaction_id = txn.id
    db.commit()

    requester = db.query(User).filter(User.id == req.requested_by_user_id).first()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="ISSUE_REQUEST_APPROVED", record_type="IssueRequest", record_id=req.id,
               new_value=f"Approved by {user.full_name}; issued to {requester.full_name}")
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="ISSUE", record_type="DocumentCopy", record_id=copy.id,
               old_value="AVAILABLE",
               new_value=f"ISSUED to {requester.full_name} ({requester.ad_username}) — via approved request",
               reason=req.purpose)
    return RedirectResponse(url="/issue-requests", status_code=303)


@router.post("/issue-requests/{request_id}/reject")
def reject_issue_request(request_id: int, request: Request, db: Session = Depends(get_db),
                          user=Depends(require_permission("DOC_ISSUE_APPROVE")),
                          decision_reason: str = Form(None)):
    req = db.query(IssueRequest).filter(IssueRequest.id == request_id).first()
    if req.status != "PENDING":
        return templates.TemplateResponse("error.html", {
            "request": request, "user": user,
            "message": f"This request is already {req.status} and can't be rejected now.",
        }, status_code=409)

    req.status = "REJECTED"
    req.decided_by_user_id = user.id
    req.decided_date = datetime.utcnow()
    req.decision_reason = decision_reason
    db.commit()

    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Documents", action="ISSUE_REQUEST_REJECTED", record_type="IssueRequest", record_id=req.id,
               new_value=f"Rejected by {user.full_name}", reason=decision_reason)
    return RedirectResponse(url="/issue-requests", status_code=303)
