"""
Password self-service and admin reset.

Design notes:
- Only accounts with a local_password_hash (local/emergency accounts, or
  any account an admin has explicitly set a password for) can change or be
  reset here. An AD-authenticated user's password lives in Active
  Directory — this app never stores it and must never offer to "change"
  it, so both routes below detect that case and point the person to their
  normal AD/Windows method instead.
- No new database column was added for this (e.g. no "must_change_password"
  flag) specifically so this feature installs on top of your existing
  database with zero schema changes. The trade-off: after an admin resets
  someone's password, the system does not force them to change it on next
  login. Document this as an SOP if your organization requires it (e.g.
  "the admin verbally tells the user to change it immediately").
- The audit trail NEVER records a plaintext password, old or new — only
  the fact that a change/reset happened, who did it, and when.
"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from ..database import get_db
from ..auth import get_current_user, require_permission
from ..audit import log_audit
from ..models import User
from ..templating import templates

router = APIRouter()

MIN_PASSWORD_LENGTH = 8


def _ip(request: Request):
    return request.client.host if request.client else None


# --------------------------------------------------------- SELF-SERVICE --

@router.get("/account/change-password")
def change_password_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("change_password.html", {
        "request": request, "user": user, "error": None, "success": None,
    })


@router.post("/account/change-password")
def change_password_submit(
    request: Request, db: Session = Depends(get_db), user=Depends(get_current_user),
    current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...),
):
    def rerender(error):
        return templates.TemplateResponse("change_password.html", {
            "request": request, "user": user, "error": error, "success": None,
        })

    if not user.local_password_hash:
        return rerender(
            "Your password is managed by your organization's IT department (Active Directory). "
            "Please change it using your normal Windows/AD method (e.g. Ctrl+Alt+Delete → Change "
            "a password) — this page can't change an AD password."
        )
    if not bcrypt.verify(current_password, user.local_password_hash):
        return rerender("Current password is incorrect.")
    if new_password != confirm_password:
        return rerender("New password and confirmation do not match.")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return rerender(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.")

    user.local_password_hash = bcrypt.hash(new_password)
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Auth", action="PASSWORD_CHANGE", record_type="User", record_id=user.id,
               reason="Self-service password change")

    return templates.TemplateResponse("change_password.html", {
        "request": request, "user": user, "error": None, "success": "Password updated successfully.",
    })


# ------------------------------------------------------------ ADMIN RESET --

@router.get("/admin/users/{user_id}/reset-password")
def reset_password_form(user_id: int, request: Request, db: Session = Depends(get_db),
                          admin_user=Depends(require_permission("USER_MANAGE"))):
    target = db.query(User).filter(User.id == user_id).first()
    if not target.local_password_hash:
        return templates.TemplateResponse("error.html", {
            "request": request, "user": admin_user,
            "message": f"{target.full_name} authenticates via Active Directory. Reset their password "
                       f"through your organization's AD/IT process — this application never stores or "
                       f"controls AD passwords.",
        }, status_code=409)
    return templates.TemplateResponse("admin_reset_password.html", {
        "request": request, "user": admin_user, "target": target, "error": None,
    })


@router.post("/admin/users/{user_id}/reset-password")
def reset_password_submit(user_id: int, request: Request, db: Session = Depends(get_db),
                            admin_user=Depends(require_permission("USER_MANAGE")),
                            new_password: str = Form(...), confirm_password: str = Form(...)):
    target = db.query(User).filter(User.id == user_id).first()

    def rerender(error):
        return templates.TemplateResponse("admin_reset_password.html", {
            "request": request, "user": admin_user, "target": target, "error": error,
        })

    if not target.local_password_hash:
        return templates.TemplateResponse("error.html", {
            "request": request, "user": admin_user,
            "message": f"{target.full_name} authenticates via Active Directory and cannot be reset here.",
        }, status_code=409)
    if new_password != confirm_password:
        return rerender("New password and confirmation do not match.")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return rerender(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    target.local_password_hash = bcrypt.hash(new_password)
    db.commit()
    log_audit(db, user_id=admin_user.id, user_name=admin_user.full_name, ip_address=_ip(request),
               module="Administration", action="PASSWORD_RESET", record_type="User", record_id=user_id,
               reason=f"Password reset by {admin_user.full_name} for {target.full_name}")

    return RedirectResponse(url="/admin/users", status_code=303)
