import os
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..auth import get_auth_provider, get_current_user
from ..audit import log_audit
from ..templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None, next: str | None = None):
    auth_mode = os.environ.get("AUTH_MODE", "LOCAL")
    return templates.TemplateResponse("login.html", {
        "request": request, "error": error, "next": next, "auth_mode": auth_mode,
    })


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...),
                  next: str = Form("/dashboard"), db: Session = Depends(get_db)):
    provider = get_auth_provider()
    result = provider.authenticate(username, password)
    client_ip = request.client.host if request.client else None

    if not result:
        log_audit(db, user_id=None, user_name=username, ip_address=client_ip,
                   module="Auth", action="LOGIN_FAILED", reason="Invalid credentials")
        return RedirectResponse(url=f"/login?error=Invalid+username+or+password&next={next}", status_code=303)

    user = db.query(User).filter(User.ad_username == result["username"]).first()
    if not user:
        # First successful AD login auto-provisions a local profile row;
        # role must still be assigned explicitly by an admin (no roles by default).
        user = User(ad_username=result["username"], full_name=result["full_name"],
                     email=result.get("email"), created_by="auth-auto-provision")
        db.add(user)
        db.commit()
        db.refresh(user)
        log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=client_ip,
                   module="Auth", action="USER_AUTO_PROVISIONED", record_type="User", record_id=user.id,
                   new_value=f"{result['username']} ({result['full_name']})",
                   reason="First successful AD login — profile created automatically, no role assigned yet")

    if user.account_status != "ACTIVE" or not user.is_active:
        log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=client_ip,
                   module="Auth", action="LOGIN_BLOCKED", reason="Account not active")
        return RedirectResponse(url="/login?error=Account+disabled", status_code=303)

    request.session["user_id"] = user.id
    request.session["user_name"] = user.full_name
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=client_ip,
               module="Auth", action="LOGIN_SUCCESS")
    # Only ever redirect to a same-site relative path — never trust `next`
    # blindly, which would otherwise be an open-redirect vector.
    safe_next = next if next and next.startswith("/") and not next.startswith("//") else "/dashboard"
    return RedirectResponse(url=safe_next, status_code=303)


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_name = request.session.get("user_name", "unknown")
    if user_id:
        log_audit(db, user_id=user_id, user_name=user_name,
                   ip_address=request.client.host if request.client else None,
                   module="Auth", action="LOGOUT")
    request.session.clear()
    return RedirectResponse(url="/login")
