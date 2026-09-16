# GMP Document Storage & Tracking System

An intranet web application for registering, locating, issuing,
returning, transferring, and auditing the physical storage location of
controlled GMP documents (SOPs, forms, protocols, etc.) within a
Document Cell / Quality Assurance department.

This project is open source — see `LICENSE` for the exact terms. Anyone
is free to download, deploy, and modify it for their own organization.

**⚠ Regulatory disclaimer:** this software is provided as-is, with no
warranty of any kind. If you deploy this for real GMP document control,
**you are solely responsible** for validating it against your own
intended use — computer system validation (IQ/OQ/PQ), risk assessment,
and regulatory compliance (21 CFR Part 11, Annex 11, or your local
equivalent) are your organization's responsibility, not something this
software can claim on your behalf. Nothing here constitutes validated,
certified, or pre-qualified software for any regulated use.

## What's in here

- `app/` — the application itself (Python, FastAPI, SQLAlchemy)
- `sql/schema_sqlserver.sql` — the production SQL Server database schema,
  generated directly from the application's own data model (so it's
  guaranteed to match what the app actually expects)
- `deployment/windows/` — Windows Service startup scripts and automated
  backup scripts (see the installation guide before filling in your own
  real values — **never commit your edited copies**, see `.gitignore`)
- `docs/` — requirements (URS/FRS), the role/permission matrix, and a
  complete, no-jargon, step-by-step installation guide covering server
  setup, database creation, audit-trail security, and per-user desktop
  setup — written for someone with no prior server/database experience

## Quick start (local demo, no SQL Server needed)

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` and log in with `local:sysadmin` /
`ChangeMe123!` — **change this password immediately** if this is anything
other than a throwaway local test. These demo credentials are
intentionally well-known and public (they're in this README); never
leave them active in a real deployment.

## Production deployment

See `docs/Installation_Guide_Complete.md` for the full walkthrough —
connecting to SQL Server, locking down the audit trail so it can never be
edited or deleted (even by application administrators), running the app
as an always-on Windows service, automated backups, and setting up a
no-install desktop shortcut for every user (their computer only needs a
browser — no local database, no local install).

## Contributing

Issues and pull requests are welcome. If you find a bug or have a feature
request, please open an issue describing what you were doing and what
happened.

## A note on secrets, for anyone deploying this

**The code in this repository is public. Your specific deployment's
secrets never should be.** Once you configure this for your own
organization, never commit:

- The database file (`gmpdoctrack.db`) — already excluded via `.gitignore`
- Any edited copy of `deployment/windows/start_server.bat` or
  `set_db_env.bat` containing your real database password or session
  secret — already excluded via `.gitignore`, but double-check before
  every commit regardless (see `docs/GitHub_Setup_Guide.md`)
- Your real company logo, user lists, document data, or storage layout,
  if you ever export any of that into a file inside this project folder

If you forked or cloned this to deploy it for your own organization,
keep *your* fork/deployment-specific branch private even though the
original project here is public — the distinction is: generic
application code is fine to share, your organization's actual data and
credentials are not.
