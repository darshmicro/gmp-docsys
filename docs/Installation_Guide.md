# Installation Guide

## A. Local demo (SQLite, LOCAL auth) — fastest way to try it

```bash
cd gmp-docsystem
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed          # creates gmpdoctrack.db + demo users
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Browse to `http://localhost:8000`. Demo logins (username / password):

| Username | Role | Password |
|---|---|---|
| local:sysadmin | System Administrator | ChangeMe123! |
| local:docadmin | Doc Cell Admin | ChangeMe123! |
| local:docuser | Doc Cell User | ChangeMe123! |
| local:viewer | Viewer | ChangeMe123! |

**Change these passwords or disable these accounts before any shared use** —
they exist for demonstration/testing only, per Section 43 of the original spec.

## B. Production deployment (SQL Server + Active Directory)

### B.1 Database
1. A DBA creates the `GMPDocTrack` database with your storage/log file
   layout and backup plan.
2. Run `sql/schema_sqlserver.sql` against it.
3. Create a **least-privilege service account** (`svc_gmpdoctrack`) and
   run the `GRANT`/`DENY` statements at the bottom of that script —
   critically, `DENY UPDATE, DELETE` on `AuditTrail` and on all
   transaction history tables.
4. Do **not** grant the application account `db_owner` or direct
   ad-hoc query rights beyond what the ORM needs.

### B.2 Application server
1. Install Python 3.11+, then:
   ```bash
   pip install -r requirements.txt
   pip install pyodbc   # SQL Server driver
   ```
2. Set environment variables (use your OS/secret manager, not a checked-in
   `.env` file):
   ```
   DATABASE_URL=mssql+pyodbc://svc_gmpdoctrack:<managed-secret>@DBSERVER/GMPDocTrack?driver=ODBC+Driver+17+for+SQL+Server
   SESSION_SECRET=<long random value from your secret manager>
   AUTH_MODE=AD
   AD_SERVER=ldap://dc01.yourcompany.local
   AD_DOMAIN=YOURCOMPANY
   AD_BASE_DN=DC=yourcompany,DC=local
   ```
3. Run behind a reverse proxy (IIS/nginx) terminating HTTPS. The app itself
   must never be exposed on plain HTTP outside the intranet segment.
4. Do **not** run the `app/seed.py` demo-user seed script against the
   production database — it's for the SQLite demo only. Populate
   `Departments`, `DocumentTypes`, `DocumentCategories`, and the initial
   storage hierarchy through the Administration UI or a controlled,
   audited data-migration script instead.
5. Map real AD groups to roles by inserting rows into
   `ADGroupRoleMapping` (or via the future Admin UI extension for it).

### B.3 First login in production
- The **first AD user to log in** is auto-provisioned with no roles
  assigned. Have a Sysadmin log in first via the emergency local account
  (create one manually with a securely generated bcrypt hash — do not
  reuse the demo password), assign themselves the SYSADMIN role's AD
  group mapping, then disable/rotate the emergency account per your
  password policy (Section 26).

## C. Configuration reference
| Env var | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./gmpdoctrack.db` |
| `SESSION_SECRET` | Cookie signing key | `dev-secret-change-me` (⚠ change in prod) |
| `AUTH_MODE` | `LOCAL` or `AD` | `LOCAL` |
| `AD_SERVER` / `AD_DOMAIN` / `AD_BASE_DN` | LDAP bind target | placeholders |

## D. Backup & Disaster Recovery (Section 34)
- **Database:** full nightly backup + transaction-log backups every 15–30
  minutes on SQL Server, per your existing GxP backup SOP; retention per
  your records-retention policy for GMP documentation.
- **Application:** the codebase and environment configuration (excluding
  secrets) should be under version control; secrets live only in your
  secret manager, never in the repo.
- **Restore testing:** schedule a periodic (e.g. quarterly) restore-to-a
  test-environment drill and log the result — this is an organizational
  procedure, not something the software automates.
