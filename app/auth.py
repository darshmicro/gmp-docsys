"""
Authentication & authorization.

- AuthProvider is an interface so the real deployment can bind to corporate
  Active Directory via LDAP without touching any route code.
- LocalAuthProvider (bcrypt) is used only for the demo and for the emergency
  local administrator account described in Section 4/26.
- ADAuthProvider shows the real LDAP bind pattern — point AD_SERVER/AD_DOMAIN
  at your environment. The application never stores the AD password: it is
  used once, in-memory, to perform the bind, and discarded.
- Server-side authorization (require_permission) is enforced on every
  protected route; front-end hiding of buttons is cosmetic only, per
  Section 38 ("never rely only on front-end permission controls").
"""
from __future__ import annotations
import os
from abc import ABC, abstractmethod
from fastapi import Request, HTTPException, Depends
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, Role


class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str) -> dict | None:
        """Return {'username':..., 'full_name':..., 'email':..., 'department':...,
        'ad_groups': [...]} on success, or None on failure. Never raises on
        bad credentials — only on infrastructure errors."""
        ...


class LocalAuthProvider(AuthProvider):
    """Demo provider + emergency local admin. Passwords are bcrypt-hashed;
    see seed.py for the demo account creation."""

    def __init__(self, db_session_factory):
        self._db_session_factory = db_session_factory

    def authenticate(self, username: str, password: str) -> dict | None:
        db = self._db_session_factory()
        try:
            user = db.query(User).filter(User.ad_username == username, User.is_active == True).first()  # noqa: E712
            if not user or not user.local_password_hash:
                return None
            if not bcrypt.verify(password, user.local_password_hash):
                return None
            return {
                "username": user.ad_username,
                "full_name": user.full_name,
                "email": user.email,
                "department": user.department.name if user.department else None,
                "ad_groups": [],
            }
        finally:
            db.close()


class ADAuthProvider(AuthProvider):
    """Real Active Directory bind via LDAP. Requires `ldap3` and network
    access to a domain controller — not usable in this sandbox, included so
    the production cut-over is a config change, not a rewrite."""

    def __init__(self, server: str, domain: str, base_dn: str):
        self.server = server
        self.domain = domain
        self.base_dn = base_dn

    def authenticate(self, username: str, password: str) -> dict | None:
        try:
            from ldap3 import Server, Connection, ALL, SUBTREE
        except ImportError:
            raise RuntimeError("ldap3 not installed — pip install ldap3")

        user_principal = f"{username}@{self.domain}"
        server = Server(self.server, get_info=ALL)
        try:
            conn = Connection(server, user=user_principal, password=password, auto_bind=True)
        except Exception:
            return None  # bad credentials or unreachable DC — treat as auth failure

        conn.search(
            self.base_dn,
            f"(sAMAccountName={username})",
            search_scope=SUBTREE,
            attributes=["displayName", "mail", "department", "memberOf"],
        )
        if not conn.entries:
            conn.unbind()
            return None
        entry = conn.entries[0]
        result = {
            "username": f"{self.domain}\\{username}",
            "full_name": str(entry.displayName) if "displayName" in entry else username,
            "email": str(entry.mail) if "mail" in entry else None,
            "department": str(entry.department) if "department" in entry else None,
            "ad_groups": [str(g) for g in entry.memberOf] if "memberOf" in entry else [],
        }
        conn.unbind()
        return result


def get_auth_provider() -> AuthProvider:
    from .database import SessionLocal
    mode = os.environ.get("AUTH_MODE", "LOCAL")  # LOCAL | AD
    if mode == "AD":
        return ADAuthProvider(
            server=os.environ.get("AD_SERVER", "ldap://dc01.company.local"),
            domain=os.environ.get("AD_DOMAIN", "COMPANY"),
            base_dn=os.environ.get("AD_BASE_DN", "DC=company,DC=local"),
        )
    return LocalAuthProvider(SessionLocal)


# ------------------------------------------------------------ SESSION / RBAC --

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()  # noqa: E712
    if not user or user.account_status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Account not active")
    return user


def require_permission(permission_code: str):
    """FastAPI dependency factory: require_permission('DOC_ISSUE')"""

    def _dep(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        from .models import RolePermission, Permission
        role_ids = [r.id for r in user.roles]
        if not role_ids:
            raise HTTPException(status_code=403, detail="No role assigned")
        has_perm = (
            db.query(RolePermission)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id.in_(role_ids), Permission.code == permission_code)
            .first()
        )
        if not has_perm:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission_code}")
        return user

    return _dep


def require_role(*role_codes: str):
    def _dep(user: User = Depends(get_current_user)):
        user_role_codes = {r.code for r in user.roles}
        if not user_role_codes.intersection(role_codes):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _dep
