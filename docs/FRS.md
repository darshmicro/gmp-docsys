# Functional Requirements Specification (FRS)
## GMP Document Storage & Tracking System

Traces to URS IDs in brackets.

## 1. Authentication & Session [UR-01]
- FR-01.1: Login form accepts DOMAIN\username + password; credential is
  passed once to the configured `AuthProvider` and never persisted.
- FR-01.2: On first successful AD login, a local user profile row is
  auto-provisioned with **no roles** — an administrator must explicitly
  assign a role before the account can do anything beyond authenticate.
- FR-01.3: Session cookie is server-signed (Starlette `SessionMiddleware`);
  production deployment must set `SESSION_SECRET` from a managed secret
  and serve over HTTPS only.
- FR-01.4: Failed logins are recorded in the audit trail with reason
  "Invalid credentials"; account lockout threshold is a configuration
  item for the deployment team (not yet wired to auto-lock in this build
  — see Known Limitations).

## 2. RBAC [UR-10, UR-15]
- FR-02.1: Permissions are rows in `Permissions`, mapped to `Roles` via
  `RolePermissions`, mapped to `Users` via `UserRoles` — fully
  configurable without code changes.
- FR-02.2: Every state-changing route depends on `require_permission(code)`
  or `require_role(code)`, enforced server-side regardless of what the
  UI displays.

## 3. Storage Hierarchy & Location Code [UR-03, UR-04]
- FR-03.1: Each of Room/Rack/Sub-Rack/Shelf/Position is its own table with
  its own FK chain (never flattened to free text).
- FR-03.2: `services/location.py::build_location_code()` derives
  `<ROOMCODE>-<RACK>-<SUBRACK>-<SHELF>-<POSITION>` (e.g.
  `DR01-R04-SR02-S03-P05`) by walking the FK chain; the result is cached
  on `Position.location_code` and `DocumentCopy.current_location_code`
  for fast search (Section 35 performance target).

## 4. Document Search [UR-02]
- FR-04.1: `/search` supports keyword (number/title), status, department,
  document type, and location-code-contains filters, combinable.
- FR-04.2: Selecting a document shows a location card with room, rack,
  sub-rack, shelf, position, full code, and current status (AVAILABLE /
  ISSUED TO: <name> / etc.) per Section 13's exact mock-up.

## 5. Issue / Return / Transfer [UR-05, UR-06, UR-07]
- FR-05.1: Issue is only permitted when `copy_status == AVAILABLE`
  (server-checked; returns HTTP 409 otherwise).
- FR-05.2: Issue creates an `IssueTransaction` row and flips
  `DocumentCopy.copy_status = ISSUED`, `current_custodian_user_id` set.
- FR-05.3: Return requires an open `IssueTransaction`; creates a
  `ReturnTransaction`, closes the issue row (`is_open=False`,
  `actual_return_datetime` set), restores `AVAILABLE` status and clears
  custodian.
- FR-05.4: Transfer creates a `TransferTransaction` recording
  `old_position_id` and `new_position_id` — the old position is **never**
  overwritten or deleted, satisfying Section 16.
- FR-05.5: Every one of the above three actions writes exactly one
  `AuditTrail` row via the single write-path in `app/audit.py`.

## 6. Audit Trail [UR-08, UR-09]
- FR-06.1: `log_audit()` is the only function in the codebase that inserts
  into `AuditTrail`; no route or service performs a direct insert.
- FR-06.2: No UPDATE or DELETE code path exists against `AuditTrail`
  anywhere in the application; in production this is additionally
  enforced with a SQL Server `DENY UPDATE, DELETE` grant (see
  `sql/schema_sqlserver.sql`, Section 8).
- FR-06.3: Timestamp is always `datetime.utcnow()` from the app/DB server,
  never client-supplied.

## 7. Dashboard [UR-11]
- FR-07.1: `/dashboard` aggregates document counts by status, storage
  counts by hierarchy level, today's transaction counts, and a live list
  of overdue issued documents (`expected_return_date < today AND
  is_open = true`).

## 8. Reports & Export [UR-12]
- FR-08.1 (Phase 2 in this build): CSV export endpoints are
  straightforward to add on top of the existing SQLAlchemy queries
  (pattern shown for `/search`); PDF export can reuse the `reportlab`
  dependency already declared in `requirements.txt`. Not wired into
  routes yet — see Known Limitations.

## 9. Data Import [UR-14]
- Architecturally supported (normalized master tables with unique
  constraints that will reject duplicates at the DB level), but the
  guided Excel/CSV import wizard UI is not built in this pass — flagged
  in Known Limitations.
