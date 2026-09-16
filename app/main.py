import os
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from .routers import auth_routes, dashboard, documents, search, storage, issue, audit_routes, admin, master_data, account, issue_requests

app = FastAPI(title="GMP Document Storage & Tracking System")


@app.exception_handler(StarletteHTTPException)
async def auth_redirect_handler(request: Request, exc: StarletteHTTPException):
    """
    - 401 (no/expired session) -> send the browser to /login. This is the
      "not authenticated at all" case, e.g. hitting /dashboard cold.
    - 403 (authenticated but lacking the required permission/role) -> render
      an Access Denied page instead. Redirecting this case to /login would
      loop forever: the user is already logged in, so logging in again just
      re-triggers the same 403 on the same page.
    API-style clients (Accept: application/json, no text/html) get the
    structured JSON error either way instead of an HTML redirect/page.
    """
    wants_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code == 401 and wants_html:
        return RedirectResponse(url=f"/login?next={request.url.path}")
    if exc.status_code == 403 and wants_html:
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="app/templates")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "user": None,
             "message": "You don't have permission to view this page. "
                        "Contact your Document Cell Admin if you believe this is incorrect."},
            status_code=403,
        )
    from starlette.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# NOTE: in production, SESSION_SECRET must come from a managed secret store,
# session cookie must be Secure+HttpOnly+SameSite=Strict, and the app must
# sit behind HTTPS termination (Section 38).
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-secret-change-me"))

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_routes.router)
app.include_router(dashboard.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(storage.router)
app.include_router(issue.router)
app.include_router(audit_routes.router)
app.include_router(admin.router)
app.include_router(master_data.router)
app.include_router(account.router)
app.include_router(issue_requests.router)


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")
