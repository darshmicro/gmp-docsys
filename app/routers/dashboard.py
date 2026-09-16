from datetime import date, datetime, timedelta
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..auth import get_current_user
from ..models import (
    Document, DocumentCopy, StorageRoom, Rack, SubRack, Shelf, Position,
    IssueTransaction, ReturnTransaction, TransferTransaction,
)
from ..templating import templates

router = APIRouter()


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    today = date.today()
    day_start = datetime.combine(today, datetime.min.time())

    doc_stats = {
        "total": db.query(Document).filter(Document.is_active == True).count(),  # noqa: E712
        "active": db.query(Document).filter(Document.status == "ACTIVE").count(),
        "superseded": db.query(Document).filter(Document.status == "SUPERSEDED").count(),
        "archived": db.query(Document).filter(Document.status == "ARCHIVED").count(),
        "obsolete": db.query(Document).filter(Document.status == "OBSOLETE").count(),
        "missing": db.query(Document).filter(Document.status == "MISSING").count(),
    }
    copy_stats = {
        "issued": db.query(DocumentCopy).filter(DocumentCopy.copy_status == "ISSUED").count(),
        "available": db.query(DocumentCopy).filter(DocumentCopy.copy_status == "AVAILABLE").count(),
    }
    storage_stats = {
        "rooms": db.query(StorageRoom).filter(StorageRoom.is_active == True).count(),  # noqa: E712
        "racks": db.query(Rack).filter(Rack.is_active == True).count(),  # noqa: E712
        "sub_racks": db.query(SubRack).filter(SubRack.is_active == True).count(),  # noqa: E712
        "shelves": db.query(Shelf).filter(Shelf.is_active == True).count(),  # noqa: E712
        "positions": db.query(Position).filter(Position.is_active == True).count(),  # noqa: E712
    }
    txn_stats = {
        "issued_today": db.query(IssueTransaction).filter(IssueTransaction.issue_datetime >= day_start).count(),
        "returned_today": db.query(ReturnTransaction).filter(ReturnTransaction.return_datetime >= day_start).count(),
        "transferred_today": db.query(TransferTransaction).filter(TransferTransaction.transfer_datetime >= day_start).count(),
    }
    overdue = (
        db.query(IssueTransaction)
        .filter(IssueTransaction.is_open == True, IssueTransaction.expected_return_date < today)  # noqa: E712
        .all()
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "doc_stats": doc_stats, "copy_stats": copy_stats,
        "storage_stats": storage_stats, "txn_stats": txn_stats, "overdue": overdue,
    })
