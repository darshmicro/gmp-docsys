"""
Single shared Jinja2Templates instance used by every router, so a Jinja2
"global" function can be registered once and be available in every
template — used here to inject the company name/logo (Section 26) into
base.html's header without having to thread it through every route's
context dict individually.
"""
from fastapi.templating import Jinja2Templates


def get_company_branding() -> dict:
    from .database import SessionLocal
    from .models import SystemConfig
    db = SessionLocal()
    try:
        name_row = db.query(SystemConfig).filter(SystemConfig.key == "COMPANY_NAME").first()
        logo_row = db.query(SystemConfig).filter(SystemConfig.key == "COMPANY_LOGO_PATH").first()
        return {
            "company_name": name_row.value if name_row and name_row.value else None,
            "company_logo": logo_row.value if logo_row and logo_row.value else None,
        }
    finally:
        db.close()


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["company_branding"] = get_company_branding
