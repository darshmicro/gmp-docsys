from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import require_permission
from ..audit import log_audit
from ..models import Department, DocumentType
from ..templating import templates

router = APIRouter()


def _ip(request: Request):
    return request.client.host if request.client else None


# ------------------------------------------------------------------ DEPARTMENTS --

@router.get("/admin/departments")
def list_departments(request: Request, db: Session = Depends(get_db),
                      user=Depends(require_permission("MASTER_EDIT"))):
    depts = db.query(Department).order_by(Department.code).all()
    return templates.TemplateResponse("departments.html", {"request": request, "user": user, "depts": depts})


@router.get("/admin/departments/new")
def new_department_form(request: Request, user=Depends(require_permission("MASTER_EDIT"))):
    return templates.TemplateResponse("department_form.html", {"request": request, "user": user, "dept": None})


@router.post("/admin/departments/new")
def create_department(request: Request, db: Session = Depends(get_db),
                       user=Depends(require_permission("MASTER_EDIT")),
                       code: str = Form(...), name: str = Form(...)):
    dept = Department(code=code, name=name, created_by=user.full_name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="CREATE", record_type="Department", record_id=dept.id,
               new_value=f"{code} - {name}")
    return RedirectResponse(url="/admin/departments", status_code=303)


@router.get("/admin/departments/{dept_id}/edit")
def edit_department_form(dept_id: int, request: Request, db: Session = Depends(get_db),
                          user=Depends(require_permission("MASTER_EDIT"))):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    return templates.TemplateResponse("department_form.html", {"request": request, "user": user, "dept": dept})


@router.post("/admin/departments/{dept_id}/edit")
def edit_department(dept_id: int, request: Request, db: Session = Depends(get_db),
                     user=Depends(require_permission("MASTER_EDIT")),
                     code: str = Form(...), name: str = Form(...), is_active: bool = Form(False)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    old = f"{dept.code} - {dept.name} (active={dept.is_active})"
    dept.code, dept.name, dept.is_active = code, name, is_active
    dept.modified_by = user.full_name
    from datetime import datetime
    dept.modified_date = datetime.utcnow()
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="UPDATE", record_type="Department", record_id=dept_id,
               old_value=old, new_value=f"{code} - {name} (active={is_active})")
    return RedirectResponse(url="/admin/departments", status_code=303)


# --------------------------------------------------------------- DOCUMENT TYPES --

@router.get("/admin/document-types")
def list_document_types(request: Request, db: Session = Depends(get_db),
                         user=Depends(require_permission("MASTER_EDIT"))):
    types = db.query(DocumentType).order_by(DocumentType.code).all()
    return templates.TemplateResponse("document_types.html", {"request": request, "user": user, "types": types})


@router.get("/admin/document-types/new")
def new_document_type_form(request: Request, user=Depends(require_permission("MASTER_EDIT"))):
    return templates.TemplateResponse("document_type_form.html", {"request": request, "user": user, "dtype": None})


@router.post("/admin/document-types/new")
def create_document_type(request: Request, db: Session = Depends(get_db),
                          user=Depends(require_permission("MASTER_EDIT")),
                          code: str = Form(...), name: str = Form(...)):
    dtype = DocumentType(code=code, name=name, created_by=user.full_name)
    db.add(dtype)
    db.commit()
    db.refresh(dtype)
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="CREATE", record_type="DocumentType", record_id=dtype.id,
               new_value=f"{code} - {name}")
    return RedirectResponse(url="/admin/document-types", status_code=303)


@router.get("/admin/document-types/{type_id}/edit")
def edit_document_type_form(type_id: int, request: Request, db: Session = Depends(get_db),
                             user=Depends(require_permission("MASTER_EDIT"))):
    dtype = db.query(DocumentType).filter(DocumentType.id == type_id).first()
    return templates.TemplateResponse("document_type_form.html", {"request": request, "user": user, "dtype": dtype})


@router.post("/admin/document-types/{type_id}/edit")
def edit_document_type(type_id: int, request: Request, db: Session = Depends(get_db),
                        user=Depends(require_permission("MASTER_EDIT")),
                        code: str = Form(...), name: str = Form(...), is_active: bool = Form(False)):
    dtype = db.query(DocumentType).filter(DocumentType.id == type_id).first()
    old = f"{dtype.code} - {dtype.name} (active={dtype.is_active})"
    dtype.code, dtype.name, dtype.is_active = code, name, is_active
    dtype.modified_by = user.full_name
    from datetime import datetime
    dtype.modified_date = datetime.utcnow()
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="UPDATE", record_type="DocumentType", record_id=type_id,
               old_value=old, new_value=f"{code} - {name} (active={is_active})")
    return RedirectResponse(url="/admin/document-types", status_code=303)
