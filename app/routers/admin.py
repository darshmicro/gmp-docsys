import os
import shutil
import uuid
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from ..database import get_db
from ..auth import require_permission
from ..audit import log_audit
from ..models import User, Role, UserRole, SystemConfig
from ..templating import templates

router = APIRouter()

UPLOAD_DIR = "app/static/uploads"


def _ip(request: Request):
    return request.client.host if request.client else None


def get_config_value(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else default


def set_config_value(db: Session, key: str, value: str, modified_by: str,
                      description: str = "", is_gmp_critical: bool = False):
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = value
        row.modified_by = modified_by
        from datetime import datetime
        row.modified_date = datetime.utcnow()
    else:
        row = SystemConfig(key=key, value=value, description=description,
                             is_gmp_critical=is_gmp_critical, modified_by=modified_by)
        db.add(row)
    db.commit()
    return row


# ------------------------------------------------------------ COMPANY SETTINGS --

@router.get("/admin/config")
def config_form(request: Request, db: Session = Depends(get_db),
                 user=Depends(require_permission("CONFIG_MANAGE"))):
    company_name = get_config_value(db, "COMPANY_NAME", "")
    logo_path = get_config_value(db, "COMPANY_LOGO_PATH", "")
    return templates.TemplateResponse("admin_config.html", {
        "request": request, "user": user, "company_name": company_name, "logo_path": logo_path,
    })


@router.post("/admin/config")
def config_save(
    request: Request, db: Session = Depends(get_db),
    user=Depends(require_permission("CONFIG_MANAGE")),
    company_name: str = Form(...), logo: UploadFile | None = File(None),
):
    old_name = get_config_value(db, "COMPANY_NAME", "")
    set_config_value(db, "COMPANY_NAME", company_name, user.full_name,
                       description="Company name shown in the application header", is_gmp_critical=True)
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Administration", action="CONFIG_CHANGE", record_type="SystemConfig",
               record_id="COMPANY_NAME", old_value=old_name, new_value=company_name)

    if logo is not None and logo.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(logo.filename)[1] or ".png"
        safe_name = f"company_logo_{uuid.uuid4().hex[:8]}{ext}"
        dest_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(logo.file, f)
        old_logo = get_config_value(db, "COMPANY_LOGO_PATH", "")
        new_logo_url = f"/static/uploads/{safe_name}"
        set_config_value(db, "COMPANY_LOGO_PATH", new_logo_url, user.full_name,
                           description="Path to the company logo image", is_gmp_critical=True)
        log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
                   module="Administration", action="CONFIG_CHANGE", record_type="SystemConfig",
                   record_id="COMPANY_LOGO_PATH", old_value=old_logo, new_value=new_logo_url)

    return RedirectResponse(url="/admin/config", status_code=303)


@router.get("/admin/users")
def list_users(request: Request, db: Session = Depends(get_db),
               user=Depends(require_permission("USER_MANAGE"))):
    users = db.query(User).all()
    roles = db.query(Role).filter(Role.is_active == True).all()  # noqa: E712
    return templates.TemplateResponse("admin_users.html", {"request": request, "user": user, "users": users, "roles": roles})


@router.get("/admin/users/new")
def new_user_form(request: Request, db: Session = Depends(get_db),
                   user=Depends(require_permission("USER_MANAGE"))):
    roles = db.query(Role).filter(Role.is_active == True).all()  # noqa: E712
    return templates.TemplateResponse("admin_user_new.html", {"request": request, "user": user, "roles": roles})


@router.post("/admin/users/new")
def create_user(
    request: Request, db: Session = Depends(get_db),
    admin_user=Depends(require_permission("USER_MANAGE")),
    username: str = Form(...), full_name: str = Form(...), email: str = Form(None),
    designation: str = Form(None), password: str = Form(...), role_id: int = Form(...),
):
    """Creates a LOCAL account directly (bypasses AD). Intended for the
    demo/local-auth deployment mode, or for emergency/service accounts in an
    AD deployment — see Section 4/26 of the URS. In AUTH_MODE=AD, real users
    should instead log in once via AD (which auto-provisions their profile)
    and simply be assigned a role here."""
    existing = db.query(User).filter(User.ad_username == username).first()
    if existing:
        return templates.TemplateResponse("error.html", {
            "request": request, "user": admin_user,
            "message": f"A user with username '{username}' already exists.",
        }, status_code=409)

    new_user = User(
        ad_username=username, full_name=full_name, email=email, designation=designation,
        is_local_emergency_account=True, local_password_hash=bcrypt.hash(password),
        created_by=admin_user.full_name,
    )
    db.add(new_user)
    db.flush()
    db.add(UserRole(user_id=new_user.id, role_id=role_id, assigned_by=admin_user.full_name))
    db.commit()

    log_audit(db, user_id=admin_user.id, user_name=admin_user.full_name, ip_address=_ip(request),
               module="Administration", action="USER_CREATE", record_type="User", record_id=new_user.id,
               new_value=f"{username} ({full_name})")
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/admin/users/{user_id}/assign-role")
def assign_role(user_id: int, request: Request, db: Session = Depends(get_db),
                 admin_user=Depends(require_permission("USER_MANAGE")),
                 role_id: int = Form(...)):
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    if not existing:
        db.add(UserRole(user_id=user_id, role_id=role_id, assigned_by=admin_user.full_name))
        db.commit()
        role = db.query(Role).filter(Role.id == role_id).first()
        log_audit(db, user_id=admin_user.id, user_name=admin_user.full_name, ip_address=_ip(request),
                   module="Administration", action="ROLE_ASSIGN", record_type="User", record_id=user_id,
                   new_value=f"role={role.code if role else role_id}")
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/admin/users/{user_id}/remove-role")
def remove_role(user_id: int, request: Request, db: Session = Depends(get_db),
                 admin_user=Depends(require_permission("USER_MANAGE")),
                 role_id: int = Form(...)):
    """Edit a user's role by removing an existing assignment (pair with
    assign-role, above, to change a user from one role to another)."""
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    if existing:
        role = db.query(Role).filter(Role.id == role_id).first()
        db.delete(existing)
        db.commit()
        log_audit(db, user_id=admin_user.id, user_name=admin_user.full_name, ip_address=_ip(request),
                   module="Administration", action="ROLE_REMOVE", record_type="User", record_id=user_id,
                   old_value=f"role={role.code if role else role_id}")
    return RedirectResponse(url="/admin/users", status_code=303)
